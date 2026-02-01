from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.tickets import tickets_bp
from app.models import Ticket, Comment, User
from app import db
from app.tickets.services import (
    calculate_sla_status,
    update_ticket_status,
    can_user_view_ticket,
    get_user_tickets
)
from datetime import datetime
from datetime import timedelta
from app.models import AssignmentRequest



@tickets_bp.route('/')
@login_required
def list_tickets():
    """List tickets with filters"""
    # Get filter parameters
    filters = {
        'status': request.args.get('status'),
        'priority': request.args.get('priority'),
        'category': request.args.get('category'),
        'assigned_to': request.args.get('assigned_to'),
        'created_by': request.args.get('created_by')
    }

    # Remove None values
    filters = {k: v for k, v in filters.items() if v}

    # Get tickets based on user role and filters
    tickets_query = get_user_tickets(current_user, filters)
    tickets = tickets_query.all()

    # Calculate SLA status for each ticket
    for ticket in tickets:
        ticket.sla_status = calculate_sla_status(ticket)

    # Get filter options
    agents = User.query.filter(User.role.in_(['agent', 'admin'])).all()

    return render_template('tickets/list.html',
                           tickets=tickets,
                           agents=agents,
                           filters=filters)


@tickets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create new ticket"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category')
        priority = request.form.get('priority')

        # Validation
        errors = {}
        if not title:
            errors['title'] = 'Title is required'
        elif len(title) > 200:
            errors['title'] = 'Title must be less than 200 characters'

        if not description:
            errors['description'] = 'Description is required'
        elif len(description) > 5000:
            errors['description'] = 'Description must be less than 5000 characters'

        if category not in ['IT', 'HR', 'Ops']:
            errors['category'] = 'Invalid category'

        if priority not in ['Low', 'Medium', 'High', 'Critical']:
            errors['priority'] = 'Invalid priority'

        if errors:
            return render_template('tickets/create.html',
                                   errors=errors,
                                   title=title,
                                   description=description,
                                   category=category,
                                   priority=priority)

        # Create ticket
        ticket = Ticket(
            title=title,
            description=description,
            category=category,
            priority=priority,
            created_by=current_user.id,
            status='OPEN',
            created_at=datetime.utcnow()
        )

        db.session.add(ticket)
        db.session.commit()

        flash(f'Ticket #{ticket.id} created successfully', 'success')
        return redirect(url_for('tickets.view_ticket', id=ticket.id))

    return render_template('tickets/create.html')


@tickets_bp.route('/<int:id>')
@login_required
def view_ticket(id):
    """View ticket detail"""
    ticket = Ticket.query.get_or_404(id)
    # 🔒 AGENT ACCESS CONTROL
    if current_user.is_agent():
        if ticket.assigned_to != current_user.id:
            abort(403)

    # Check permission
    if not can_user_view_ticket(ticket, current_user):
        flash('Access denied. You do not have permission to view this ticket.', 'error')
        abort(403)

    # Calculate SLA status
    ticket.sla_status = calculate_sla_status(ticket)

    # Get comments with authors
    comments = Comment.query.filter_by(ticket_id=id).order_by(Comment.created_at.asc()).all()

    # Get available agents for assignment (admin/agent only)
    agents = None
    if current_user.is_admin() or current_user.is_agent():
        agents = User.query.filter(User.role.in_(['agent', 'admin'])).all()

    return render_template('tickets/detail.html',
                           ticket=ticket,
                           comments=comments,
                           agents=agents)


@tickets_bp.route('/<int:id>/comment', methods=['POST'])
@login_required
def add_comment(id):
    """Add comment to ticket"""
    ticket = Ticket.query.get_or_404(id)
  
	# 🔒 HARD LOCK: no comments on CLOSED tickets
    if ticket.status == 'CLOSED':
        flash("This ticket is closed and read-only.", "error")
        return redirect(url_for('tickets.view_ticket', id=id))
      
    # Check permission
    if not can_user_view_ticket(ticket, current_user):
        flash('Access denied.', 'error')
        abort(403)

    text = request.form.get('text', '').strip()

    # Validation
    if not text:
        flash('Comment text is required', 'error')
        return redirect(url_for('tickets.view_ticket', id=id))

    if len(text) > 2000:
        flash('Comment must be less than 2000 characters', 'error')
        return redirect(url_for('tickets.view_ticket', id=id))

    # Create comment
    comment = Comment(
        ticket_id=id,
        user_id=current_user.id,
        text=text,
        created_at=datetime.utcnow()
    )

    db.session.add(comment)
    db.session.commit()

    flash('Comment added', 'success')
    return redirect(url_for('tickets.view_ticket', id=id))


@tickets_bp.route('/<int:id>/status', methods=['POST'])
@login_required
def update_status(id):
    """Update ticket status with strict RBAC"""
    ticket = Ticket.query.get_or_404(id)

    new_status = request.form.get('status')

    # ================= RBAC RULES =================

    # AGENT: can only update if assigned to them
    if current_user.is_agent():
        if ticket.assigned_to != current_user.id:
            abort(403)

        # Agent allowed transitions
        if new_status not in ['IN_PROGRESS', 'RESOLVED']:
            abort(403)

    # ADMIN: can ONLY reopen resolved/closed tickets
    elif current_user.is_admin():
        if new_status != 'IN_PROGRESS' or ticket.status not in ['RESOLVED', 'CLOSED']:
            abort(403)

    # USER: never allowed
    else:
        abort(403)

    # =============================================

    try:
        update_ticket_status(id, new_status, current_user)
        flash(f'Ticket status updated to {new_status}', 'success')
    except Exception as e:
        flash(str(e), 'error')

    return redirect(url_for('tickets.view_ticket', id=id))



@tickets_bp.route('/<int:id>/assign', methods=['POST'])
@login_required
def assign_ticket(id):
    """Assign ticket to agent (ADMIN ONLY)"""

    # 🔒 HARD RBAC CHECK
    if not current_user.is_admin():
        flash('Access denied. Only admins can assign tickets.', 'error')
        abort(403)

    ticket = Ticket.query.get_or_404(id)

    agent_id = request.form.get('agent_id')
    if ticket.status == 'CLOSED':
        abort(409)  # conflict

    # Handle unassignment
    if not agent_id or agent_id == '':
        ticket.assigned_to = None
        db.session.commit()
        flash('Ticket unassigned', 'success')
        return redirect(url_for('tickets.view_ticket', id=id))

    # Validate agent
    agent = User.query.get(agent_id)
    if not agent or agent.role != 'agent':
        flash('Invalid agent selected', 'error')
        return redirect(url_for('tickets.view_ticket', id=id))

    # Assign ticket
    ticket.assigned_to = agent.id
    db.session.commit()

    flash(f'Ticket assigned to {agent.name}', 'success')
    return redirect(url_for('tickets.view_ticket', id=id))


@tickets_bp.route('/<int:id>/request-assignment', methods=['POST'])
@login_required
def request_assignment(id):
    """Agent requests assignment for an unassigned ticket (after 24h)"""

    # 🔒 Only agents
    if not current_user.is_agent():
        abort(403)

    ticket = Ticket.query.get_or_404(id)

    # ✅ Single source of truth (24h + unassigned)
    if not ticket.can_request_assignment():
        flash("This ticket is not eligible for assignment request yet.", "error")
        return redirect(url_for('main.agent_dashboard'))

    # 🚫 Prevent parallel requests by multiple agents
    existing_pending = AssignmentRequest.query.filter_by(
        ticket_id=id,
        status='PENDING'
    ).first()

    if existing_pending:
        flash("Another agent has already requested this ticket.", "info")
        return redirect(url_for('main.agent_dashboard'))

    # 🚫 Prevent same agent duplicate pending request
    existing_agent_req = AssignmentRequest.query.filter_by(
        ticket_id=id,
        agent_id=current_user.id,
        status='PENDING'
    ).first()

    if existing_agent_req:
        flash("You already have a pending request for this ticket.", "info")
        return redirect(url_for('main.agent_dashboard'))

    # ✅ Create request
    req = AssignmentRequest(
        ticket_id=id,
        agent_id=current_user.id,
        status='PENDING'
    )

    db.session.add(req)
    db.session.commit()

    flash("Assignment request sent to admin.", "success")
    return redirect(url_for('main.agent_dashboard'))
  
@tickets_bp.route('/<int:id>/close', methods=['POST'])
@login_required
def close_ticket(id):
    ticket = Ticket.query.get_or_404(id)

    # Only RESOLVED tickets can be closed
    if ticket.status != 'RESOLVED':
        flash("Only resolved tickets can be closed.", "error")
        return redirect(url_for('tickets.view_ticket', id=id))

    # Permission: ticket owner OR admin
    is_owner = ticket.created_by == current_user.id
    is_admin = current_user.is_admin()

    if not (is_owner or is_admin):
        abort(403)

    ticket.status = 'CLOSED'
    db.session.commit()

    flash("Ticket closed successfully.", "success")
    return redirect(url_for('tickets.view_ticket', id=id))

@tickets_bp.route('/<int:id>/reopen', methods=['POST'])
@login_required
def reopen_ticket(id):
    ticket = Ticket.query.get_or_404(id)

    # Only RESOLVED tickets can be reopened
    if ticket.status != 'RESOLVED':
        flash("Only resolved tickets can be reopened.", "error")
        return redirect(url_for('tickets.view_ticket', id=id))

    # Permission: ticket owner OR admin
    is_owner = ticket.created_by == current_user.id
    is_admin = current_user.is_admin()

    if not (is_owner or is_admin):
        abort(403)

    ticket.status = 'IN_PROGRESS'
    ticket.resolved_at = None
    db.session.commit()

    flash("Ticket reopened and moved back to In Progress.", "success")
    return redirect(url_for('tickets.view_ticket', id=id))


@tickets_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_ticket(id):
    ticket = Ticket.query.get_or_404(id)

    if ticket.created_by != current_user.id:
        abort(403)

    if ticket.assigned_to is not None or ticket.status != 'OPEN':
        flash("Only unassigned open tickets can be edited.", "error")
        return redirect(url_for('tickets.view_ticket', id=id))

    if request.method == 'POST':
        ticket.title = request.form['title']
        ticket.description = request.form['description']
        ticket.priority = request.form['priority']
        ticket.category = request.form['category']
        db.session.commit()

        flash("Ticket updated successfully.", "success")
        return redirect(url_for('tickets.view_ticket', id=id))

    return render_template('tickets/edit.html', ticket=ticket)

@tickets_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_ticket(id):
    ticket = Ticket.query.get_or_404(id)

    if ticket.created_by != current_user.id:
        abort(403)

    if ticket.assigned_to is not None:
        flash("Assigned tickets cannot be deleted.", "error")
        return redirect(url_for('tickets.view_ticket', id=id))

    ticket.is_deleted = True
    db.session.commit()

    flash("Ticket removed from your view.", "success")
    return redirect(url_for('main.dashboard'))
