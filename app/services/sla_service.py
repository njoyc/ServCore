from datetime import datetime, timedelta

# SLA rules in hours
SLA_HOURS = {
    "CRITICAL": 4,
    "HIGH": 24,
    "MEDIUM": 48,
    "LOW": 72
}


def calculate_sla_status(ticket):
    """
    Returns:
    {
        status: "ok" | "breached",
        remaining: timedelta | None,
        overdue: bool
    }
    """

    if not ticket.created_at:
        return None

    priority = ticket.priority.upper()
    sla_hours = SLA_HOURS.get(priority, 72)

    deadline = ticket.created_at + timedelta(hours=sla_hours)

    now = datetime.utcnow()

    # If already resolved
    if ticket.resolved_at:
        if ticket.resolved_at <= deadline:
            return {
                "status": "ok",
                "remaining": timedelta(seconds=0),
                "overdue": False
            }
        else:
            return {
                "status": "breached",
                "remaining": timedelta(seconds=0),
                "overdue": True
            }

    # Not resolved yet
    if now <= deadline:
        return {
            "status": "ok",
            "remaining": deadline - now,
            "overdue": False
        }
    else:
        return {
            "status": "breached",
            "remaining": timedelta(seconds=0),
            "overdue": True
        }
