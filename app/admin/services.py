from sqlalchemy import func
from datetime import datetime, timedelta
from app.models import Ticket, User
from app import db


def get_overview_stats():
    """
    Get overview statistics for admin dashboard

    Returns:
        dict: Overview statistics
    """
    # Total tickets
    total_tickets = Ticket.query.count()

    # Open tickets
    open_tickets = Ticket.query.filter_by(status='OPEN').count()

    # Closed tickets
    closed_tickets = Ticket.query.filter_by(status='CLOSED').count()

    # Tickets created today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tickets_today = Ticket.query.filter(Ticket.created_at >= today_start).count()

    # Tickets resolved today
    resolved_today = Ticket.query.filter(
        Ticket.status == 'RESOLVED',
        Ticket.resolved_at >= today_start
    ).count()

    # Average resolution time (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    resolved_tickets = Ticket.query.filter(
        Ticket.resolved_at.isnot(None),
        Ticket.resolved_at >= thirty_days_ago
    ).all()

    if resolved_tickets:
        total_resolution_time = sum([
            (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
            for ticket in resolved_tickets
        ])
        avg_resolution_time = total_resolution_time / len(resolved_tickets)
    else:
        avg_resolution_time = 0

    # SLA compliance rate
    if resolved_tickets:
        compliant_count = sum([
            1 for ticket in resolved_tickets
            if (ticket.resolved_at - ticket.created_at).total_seconds() / 3600 <= ticket.get_sla_target()
        ])
        sla_compliance_rate = (compliant_count / len(resolved_tickets)) * 100
    else:
        sla_compliance_rate = 0

    return {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'closed_tickets': closed_tickets,
        'tickets_today': tickets_today,
        'resolved_today': resolved_today,
        'avg_resolution_time': round(avg_resolution_time, 1),
        'sla_compliance_rate': round(sla_compliance_rate, 1)
    }


def get_tickets_by_status():
    """
    Get ticket counts grouped by status

    Returns:
        list: List of dicts with status and count
    """
    results = db.session.query(
        Ticket.status,
        func.count(Ticket.id).label('count')
    ).group_by(Ticket.status).all()

    return [{'status': row.status, 'count': row.count} for row in results]


def get_tickets_by_priority():
    """
    Get ticket counts grouped by priority

    Returns:
        list: List of dicts with priority and count
    """
    results = db.session.query(
        Ticket.priority,
        func.count(Ticket.id).label('count')
    ).group_by(Ticket.priority).all()

    return [{'priority': row.priority, 'count': row.count} for row in results]


def get_tickets_by_category():
    """
    Get ticket counts grouped by category

    Returns:
        list: List of dicts with category and count
    """
    results = db.session.query(
        Ticket.category,
        func.count(Ticket.id).label('count')
    ).group_by(Ticket.category).all()

    return [{'category': row.category, 'count': row.count} for row in results]


def get_agent_performance():
    """
    Get performance statistics for each agent

    Returns:
        list: List of dicts with agent statistics
    """
    agents = User.query.filter(User.role.in_(['agent', 'admin'])).all()

    agent_stats = []
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    for agent in agents:
        # Currently assigned tickets
        assigned_count = Ticket.query.filter_by(assigned_to=agent.id).count()

        # Resolved tickets in last 30 days
        resolved_tickets = Ticket.query.filter(
            Ticket.assigned_to == agent.id,
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at >= thirty_days_ago
        ).all()

        resolved_count = len(resolved_tickets)

        # Average resolution time
        if resolved_tickets:
            total_resolution_time = sum([
                (ticket.resolved_at - ticket.created_at).total_seconds() / 3600
                for ticket in resolved_tickets
            ])
            avg_resolution_time = total_resolution_time / len(resolved_tickets)

            # SLA compliance
            compliant_count = sum([
                1 for ticket in resolved_tickets
                if (ticket.resolved_at - ticket.created_at).total_seconds() / 3600 <= ticket.get_sla_target()
            ])
            sla_compliance = (compliant_count / len(resolved_tickets)) * 100
        else:
            avg_resolution_time = 0
            sla_compliance = 0

        agent_stats.append({
            'name': agent.name,
            'assigned_count': assigned_count,
            'resolved_count': resolved_count,
            'avg_resolution_time': round(avg_resolution_time, 1),
            'sla_compliance': round(sla_compliance, 1)
        })

    # Sort by assigned count (descending)
    agent_stats.sort(key=lambda x: x['assigned_count'], reverse=True)

    return agent_stats


def get_resolution_time_trend(days=30):
    """
    Get average resolution time trend over specified days

    Args:
        days: Number of days to look back

    Returns:
        list: List of dicts with date and average resolution time
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get resolved tickets in date range
    resolved_tickets = Ticket.query.filter(
        Ticket.resolved_at.isnot(None),
        Ticket.resolved_at >= start_date
    ).all()

    # Group by date and calculate average
    date_groups = {}
    for ticket in resolved_tickets:
        date_key = ticket.resolved_at.date()
        resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 3600

        if date_key not in date_groups:
            date_groups[date_key] = []
        date_groups[date_key].append(resolution_time)

    # Calculate averages
    trend_data = []
    for date_key in sorted(date_groups.keys()):
        avg_time = sum(date_groups[date_key]) / len(date_groups[date_key])
        trend_data.append({
            'date': date_key.isoformat(),
            'avg_hours': round(avg_time, 1)
        })

    return trend_data


def get_recent_activity(limit=20):
    """
    Get recent ticket activity

    Args:
        limit: Number of recent tickets to return

    Returns:
        list: Recent tickets with activity
    """
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(limit).all()

    activity = []
    for ticket in tickets:
        activity.append({
            'id': ticket.id,
            'title': ticket.title,
            'status': ticket.status,
            'created_by': ticket.creator.name,
            'created_at': ticket.created_at
        })

    return activity
