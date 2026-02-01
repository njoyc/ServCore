from datetime import datetime
from app.models import Ticket
from app import db


def calculate_sla_status(ticket):
    """
    Calculate SLA status for a ticket

    Args:
        ticket: Ticket model instance

    Returns:
        dict: SLA status information with keys:
            - target_hours: SLA target based on priority
            - elapsed_hours: Hours since ticket creation
            - remaining_hours: Hours until SLA breach (negative if overdue)
            - is_overdue: Boolean indicating SLA breach
            - status_class: CSS class for styling
            - display_text: Human-readable status text
    """
    target_hours = ticket.get_sla_target()

    # For resolved or closed tickets
    if ticket.status in ['RESOLVED', 'CLOSED']:
        if ticket.resolved_at:
            elapsed_seconds = (ticket.resolved_at - ticket.created_at).total_seconds()
            elapsed_hours = elapsed_seconds / 3600
            is_overdue = elapsed_hours > target_hours
            remaining_hours = target_hours - elapsed_hours

            return {
                'target_hours': target_hours,
                'elapsed_hours': elapsed_hours,
                'remaining_hours': remaining_hours,
                'is_overdue': is_overdue,
                'status_class': 'sla-overdue' if is_overdue else 'sla-ok',
                'display_text': format_sla_time(elapsed_hours, is_resolved=True, is_overdue=is_overdue)
            }

    # For open or in-progress tickets
    elapsed_seconds = (datetime.utcnow() - ticket.created_at).total_seconds()
    elapsed_hours = elapsed_seconds / 3600
    remaining_hours = target_hours - elapsed_hours
    is_overdue = remaining_hours < 0

    # Determine status class
    if is_overdue:
        status_class = 'sla-overdue'
    elif remaining_hours < 2:
        status_class = 'sla-warning'
    else:
        status_class = 'sla-ok'

    return {
        'target_hours': target_hours,
        'elapsed_hours': elapsed_hours,
        'remaining_hours': remaining_hours,
        'is_overdue': is_overdue,
        'status_class': status_class,
        'display_text': format_sla_time(abs(remaining_hours), is_resolved=False, is_overdue=is_overdue)
    }


def format_sla_time(hours, is_resolved=False, is_overdue=False):
    """
    Format hours into human-readable time string

    Args:
        hours: Number of hours (float)
        is_resolved: Whether ticket is resolved
        is_overdue: Whether SLA is breached

    Returns:
        str: Formatted time string
    """
    if hours < 1:
        minutes = int(hours * 60)
        time_str = f"{minutes}m"
    elif hours < 24:
        h = int(hours)
        m = int((hours - h) * 60)
        time_str = f"{h}h {m}m" if m > 0 else f"{h}h"
    else:
        days = int(hours / 24)
        h = int(hours % 24)
        time_str = f"{days}d {h}h" if h > 0 else f"{days}d"

    if is_resolved:
        return f"Resolved in {time_str}" + (" (overdue)" if is_overdue else " (within SLA)")
    else:
        return f"{time_str} overdue" if is_overdue else f"{time_str} remaining"


def validate_status_transition(current_status, new_status):
    """
    Validate if status transition is allowed

    Args:
        current_status: Current ticket status
        new_status: Target status

    Returns:
        bool: True if transition is valid, False otherwise
    """
    valid_transitions = {
        'OPEN': ['IN_PROGRESS'],
        'IN_PROGRESS': ['OPEN', 'RESOLVED'],
        'RESOLVED': ['IN_PROGRESS', 'CLOSED'],
        'CLOSED': []  # Final state, no transitions allowed
    }

    allowed_statuses = valid_transitions.get(current_status, [])
    return new_status in allowed_statuses


def update_ticket_status(ticket_id, new_status, user):
    """
    Update ticket status with workflow validation

    Args:
        ticket_id: ID of ticket to update
        new_status: Target status
        user: User performing the update

    Returns:
        Ticket: Updated ticket object

    Raises:
        ValueError: If transition is invalid
        PermissionError: If user doesn't have permission
    """
    ticket = Ticket.query.get_or_404(ticket_id)
  	# 🔒 HARD LOCK: CLOSED tickets are immutable
    if ticket.status == 'CLOSED':
    	raise ValueError("Closed tickets cannot be modified.")

    # Check permissions
    if not (user.is_admin() or user.is_agent() or ticket.created_by == user.id):
        raise PermissionError("You don't have permission to update this ticket")

    # Validate transition
    if not validate_status_transition(ticket.status, new_status):
        raise ValueError(f"Invalid status transition from {ticket.status} to {new_status}")

    # Update status
    ticket.status = new_status

    # Set resolved_at timestamp when moving to RESOLVED
    if new_status == 'RESOLVED' and ticket.resolved_at is None:
        ticket.resolved_at = datetime.utcnow()

    # Clear resolved_at when reopening from RESOLVED
    if new_status == 'IN_PROGRESS' and ticket.status == 'RESOLVED':
        ticket.resolved_at = None

    db.session.commit()
    return ticket


def can_user_view_ticket(ticket, user):
    """
    Check if user has permission to view ticket

    Args:
        ticket: Ticket model instance
        user: User model instance

    Returns:
        bool: True if user can view ticket
    """
    # Admins can view all tickets
    if user.is_admin():
        return True

    # Agents can view assigned tickets and unassigned tickets
    if user.is_agent():
        return ticket.assigned_to is None or ticket.assigned_to == user.id

    # Users can only view their own tickets
    return ticket.created_by == user.id


def get_user_tickets(user, filters=None):
    """
    Get tickets visible to user with optional filters

    Args:
        user: User model instance
        filters: Dictionary of filter criteria

    Returns:
        Query: Filtered ticket query
    """
    # Base query depends on user role
    if user.is_admin():
        query = Ticket.query
    elif user.is_agent():
        # Agents see assigned tickets + unassigned tickets
        query = Ticket.query.filter(
            db.or_(
                Ticket.assigned_to == user.id,
                Ticket.assigned_to == None
            )
        )
    else:
        # Users see only their own tickets
        query = Ticket.query.filter_by(created_by=user.id)

    # Apply filters if provided
    if filters:
        if filters.get('status'):
            statuses = filters['status'].split(',')
            query = query.filter(Ticket.status.in_(statuses))

        if filters.get('priority'):
            query = query.filter_by(priority=filters['priority'])

        if filters.get('category'):
            query = query.filter_by(category=filters['category'])

        if filters.get('assigned_to'):
            query = query.filter_by(assigned_to=filters['assigned_to'])

        if filters.get('created_by'):
            query = query.filter_by(created_by=filters['created_by'])

    return query.order_by(Ticket.created_at.desc())
