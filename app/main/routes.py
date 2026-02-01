from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import main_bp
from app.models import Ticket
from app.auth.decorators import role_required
from datetime import datetime, timedelta


@main_bp.route('/')
def index():
    """Home page - redirect to appropriate dashboard"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_agent():
            return redirect(url_for('main.agent_dashboard'))
        else:
            return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing own tickets"""
    # Get user's tickets
    tickets = Ticket.query.filter_by(created_by=current_user.id).order_by(Ticket.created_at.desc()).all()

    # Calculate statistics
    total_tickets = len(tickets)
    open_tickets = len([t for t in tickets if t.status == 'OPEN'])
    in_progress_tickets = len([t for t in tickets if t.status == 'IN_PROGRESS'])

    # Resolved tickets in last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    resolved_recent = len([t for t in tickets if t.status == 'RESOLVED' and t.resolved_at and t.resolved_at > thirty_days_ago])

    # Recent tickets (last 10)
    recent_tickets = tickets[:10]

    return render_template('main/user_dashboard.html',
                           tickets=tickets,
                           recent_tickets=recent_tickets,
                           total_tickets=total_tickets,
                           open_tickets=open_tickets,
                           in_progress_tickets=in_progress_tickets,
                           resolved_recent=resolved_recent)


@main_bp.route('/agent/dashboard')
@role_required('agent')
def agent_dashboard():
    """Agent dashboard showing assigned and unassigned tickets"""

    # Assigned tickets
    assigned_tickets = (
        Ticket.query
        .filter_by(assigned_to=current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )

    # Unassigned + OPEN tickets only
    unassigned_tickets = (
        Ticket.query
        .filter_by(assigned_to=None, status='OPEN')
        .order_by(Ticket.created_at.desc())
        .all()
    )

    # Stats
    total_assigned = len(assigned_tickets)
    in_progress_count = len([t for t in assigned_tickets if t.status == 'IN_PROGRESS'])

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    resolved_today = len([
        t for t in assigned_tickets
        if t.status == 'RESOLVED' and t.resolved_at and t.resolved_at >= today_start
    ])

    overdue_count = len([t for t in assigned_tickets if t.is_overdue()])

    # Sort assigned tickets (overdue first)
    assigned_tickets_sorted = sorted(
        assigned_tickets,
        key=lambda t: (not t.is_overdue(), t.created_at)
    )

    # ---- Assignment request flags (CLEAN, MODEL-DRIVEN) ----
    for ticket in unassigned_tickets:
        ticket.can_request = ticket.can_request_assignment()
        ticket.request_pending = ticket.has_pending_request_from(current_user.id)

    return render_template(
        'main/agent_dashboard.html',
        assigned_tickets=assigned_tickets_sorted,
        unassigned_tickets=unassigned_tickets,
        total_assigned=total_assigned,
        in_progress_count=in_progress_count,
        resolved_today=resolved_today,
        overdue_count=overdue_count
    )

