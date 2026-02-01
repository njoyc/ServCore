from functools import wraps
from flask import flash, abort
from flask_login import current_user, login_required


def role_required(roles):
    """
    Decorator to restrict route access based on user role

    Args:
        roles: Single role string or list of allowed roles

    Usage:
        @role_required('admin')
        @role_required(['admin', 'agent'])
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Convert single role to list for uniform handling
            allowed_roles = roles if isinstance(roles, list) else [roles]

            # Check if current user's role is in allowed roles
            if current_user.role not in allowed_roles:
                flash('Access denied. You do not have permission to access this page.', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator
