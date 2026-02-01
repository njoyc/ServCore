from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    """User model for authentication and role management"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('user', 'agent', 'admin', name='user_roles'), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_tickets = db.relationship('Ticket', foreign_keys='Ticket.created_by', backref='creator', lazy='dynamic')
    assigned_tickets = db.relationship('Ticket', foreign_keys='Ticket.assigned_to', backref='assignee', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user has admin role"""
        return self.role == 'admin'

    def is_agent(self):
        """Check if user has agent role"""
        return self.role == 'agent'

    def is_user(self):
        """Check if user has user role"""
        return self.role == 'user'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Ticket(db.Model):
    """Ticket model for support requests"""
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum('IT', 'HR', 'Ops', name='ticket_categories'), nullable=False)
    priority = db.Column(db.Enum('Low', 'Medium', 'High', 'Critical', name='ticket_priorities'), nullable=False)
    status = db.Column(db.Enum('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticket_statuses'),
                       nullable=False, default='OPEN')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    comments = db.relationship('Comment', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')

    def get_resolution_time(self):
        """
        Calculate time taken to resolve ticket

        Returns:
            timedelta or None: Resolution time if resolved, None otherwise
        """
        if self.resolved_at:
            return self.resolved_at - self.created_at
        return None

    def get_sla_target(self):
        """
        Get SLA target hours based on priority

        Returns:
            int: Target hours for this priority level
        """
        sla_targets = {
            'Critical': 4,
            'High': 24,
            'Medium': 48,
            'Low': 72
        }
        return sla_targets.get(self.priority, 72)

    def is_overdue(self):
        """
        Check if ticket has breached SLA

        Returns:
            bool: True if ticket is overdue, False otherwise
        """
        if self.status in ['RESOLVED', 'CLOSED']:
            return False

        elapsed_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        return elapsed_hours > self.get_sla_target()

    def can_transition_to(self, new_status):
        """
        Validate if status transition is allowed

        Args:
            new_status: Target status to transition to

        Returns:
            bool: True if transition is valid, False otherwise
        """
        valid_transitions = {
            'OPEN': ['IN_PROGRESS'],
            'IN_PROGRESS': ['OPEN', 'RESOLVED'],
            'RESOLVED': ['IN_PROGRESS', 'CLOSED'],
            'CLOSED': []  # Final state, no transitions allowed
        }

        allowed_statuses = valid_transitions.get(self.status, [])
        return new_status in allowed_statuses

    '''def can_request_assignment(self):
        """
        Agent can request assignment only if:
        - Ticket is unassigned
        - Ticket is OPEN
        - Ticket is older than 24 hours
        """
        if self.assigned_to is not None:
            return False
    
        if self.status != 'OPEN':
            return False
    
        return datetime.utcnow() >= self.created_at + timedelta(hours=24)'''

    def hours_since_creation(self):
        return (datetime.utcnow() - self.created_at).total_seconds() / 3600
    
    
    def can_request_assignment(self):
        return (
            self.assigned_to is None and
            self.status == 'OPEN' and
            self.hours_since_creation() >= 24
        )

    
    
    def has_pending_request_from(self, agent_id):
        return any(
            r.agent_id == agent_id and r.status == 'PENDING'
            for r in self.assignment_requests
        )


    def __repr__(self):
        return f'<Ticket #{self.id}: {self.title} ({self.status})>'


class Comment(db.Model):
    """Comment model for ticket discussions"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<Comment #{self.id} on Ticket #{self.ticket_id}>'


class AssignmentRequest(db.Model):
    __tablename__ = 'assignment_requests'

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    status = db.Column(
        db.Enum('PENDING', 'APPROVED', 'REJECTED', name='assignment_request_status'),
        nullable=False,
        default='PENDING',
      	index=True
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    ticket = db.relationship('Ticket', backref='assignment_requests')
    agent = db.relationship('User', backref='assignment_requests')

    __table_args__ = (
        db.UniqueConstraint(
            'ticket_id',
            'agent_id',
            name='uq_ticket_agent_request'
        ),
    )


