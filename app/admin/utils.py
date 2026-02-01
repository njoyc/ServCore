from flask_login import current_user
from app.models import AssignmentRequest

def pending_assignment_count():
    return AssignmentRequest.query.filter_by(status='PENDING').count()


def admin_context_processor():
    if current_user.is_authenticated and current_user.is_admin():
        return {
            'pending_assignment_count': pending_assignment_count()
        }
    return {}
