from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.auth.decorators import role_required
from app.models import User, AssignmentRequest, Ticket
from app import db
from datetime import datetime
from app.admin.services import (
    get_overview_stats,
    get_tickets_by_status,
    get_tickets_by_priority,
    get_tickets_by_category,
    get_agent_performance,
    get_resolution_time_trend,
    get_recent_activity
)
import json


@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    """Admin analytics dashboard"""
    # Get all statistics
    overview = get_overview_stats()
    status_data = get_tickets_by_status()
    priority_data = get_tickets_by_priority()
    category_data = get_tickets_by_category()
    agent_performance = get_agent_performance()
    trend_data = get_resolution_time_trend(30)
    recent_activity = get_recent_activity(20)

    # Convert data to JSON for charts
    status_json = json.dumps(status_data)
    priority_json = json.dumps(priority_data)
    category_json = json.dumps(category_data)
    trend_json = json.dumps(trend_data)

    return render_template('admin/dashboard.html',
                           overview=overview,
                           status_data=status_json,
                           priority_data=priority_json,
                           category_data=category_json,
                           trend_data=trend_json,
                           agent_performance=agent_performance,
                           recent_activity=recent_activity)


@admin_bp.route('/users')
@role_required('admin')
def list_users():
    """List all users"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@role_required('admin')
def create_user():
    """Create new user"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role')

        # Validation
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) > 100:
            errors['name'] = 'Name must be less than 100 characters'

        if not email:
            errors['email'] = 'Email is required'
        elif User.query.filter_by(email=email).first():
            errors['email'] = 'Email already exists'

        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'

        if role not in ['user', 'agent', 'admin']:
            errors['role'] = 'Invalid role'

        if errors:
            return render_template('admin/user_form.html',
                                   errors=errors,
                                   name=name,
                                   email=email,
                                   role=role,
                                   action='create')

        # Create user
        user = User(name=name, email=email, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f'User {name} created successfully', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', action='create')


@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_user(id):
    """Edit existing user"""
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role')

        # Validation
        errors = {}
        if not name:
            errors['name'] = 'Name is required'
        elif len(name) > 100:
            errors['name'] = 'Name must be less than 100 characters'

        if not email:
            errors['email'] = 'Email is required'
        else:
            # Check email uniqueness (excluding current user)
            existing = User.query.filter(User.email == email, User.id != id).first()
            if existing:
                errors['email'] = 'Email already exists'

        if password and len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'

        if role not in ['user', 'agent', 'admin']:
            errors['role'] = 'Invalid role'

        if errors:
            return render_template('admin/user_form.html',
                                   errors=errors,
                                   user=user,
                                   name=name,
                                   email=email,
                                   role=role,
                                   action='edit')

        # Update user
        user.name = name
        user.email = email
        user.role = role

        # Update password if provided
        if password:
            user.set_password(password)

        db.session.commit()

        flash(f'User {name} updated successfully', 'success')
        return redirect(url_for('admin.list_users'))

    return render_template('admin/user_form.html', user=user, action='edit')


@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(id):
    """Delete user"""
    user = User.query.get_or_404(id)

    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin.list_users'))

    # Check for assigned tickets
    assigned_tickets = Ticket.query.filter_by(assigned_to=id).count()
    if assigned_tickets > 0:
        flash(f'Cannot delete user. User has {assigned_tickets} assigned tickets. Reassign them first.', 'error')
        return redirect(url_for('admin.list_users'))

    # Delete user
    db.session.delete(user)
    db.session.commit()

    flash(f'User {user.name} deleted successfully', 'success')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/assign')
@role_required('admin')
def assign_tickets():
    """Ticket assignment interface"""
    # Get unassigned tickets
    unassigned_tickets = Ticket.query.filter_by(assigned_to=None).order_by(Ticket.created_at.desc()).all()

    # Get all agents with workload
    agents = User.query.filter(User.role.in_(['agent', 'admin'])).all()

    agent_workload = []
    for agent in agents:
        workload = Ticket.query.filter_by(assigned_to=agent.id).count()
        agent_workload.append({
            'id': agent.id,
            'name': agent.name,
            'workload': workload
        })

    # Sort by workload
    agent_workload.sort(key=lambda x: x['workload'])

    return render_template('admin/assign.html',
                           unassigned_tickets=unassigned_tickets,
                           agents=agent_workload)


@admin_bp.route('/assign/<int:ticket_id>', methods=['POST'])
@role_required('admin')
def assign_ticket_action(ticket_id):
    """Assign ticket to agent"""
    ticket = Ticket.query.get_or_404(ticket_id)

    agent_id = request.form.get('agent_id')

    # Validate agent
    if not agent_id:
        flash('Please select an agent', 'error')
        return redirect(url_for('admin.assign_tickets'))

    agent = User.query.get(agent_id)
    if not agent or agent.role not in ['agent', 'admin']:
        flash('Invalid agent selected', 'error')
        return redirect(url_for('admin.assign_tickets'))

    # Assign ticket
    ticket.assigned_to = agent.id
    ticket.status = 'IN_PROGRESS'
    AssignmentRequest.query.filter(
        AssignmentRequest.ticket_id == ticket.id,
        AssignmentRequest.status == 'PENDING'
    ).update({'status': 'REJECTED'})

    db.session.commit()

    flash(f'Ticket #{ticket.id} assigned to {agent.name}', 'success')
    return redirect(url_for('admin.assign_tickets'))

@admin_bp.route('/assignment-requests')
@role_required('admin')
def assignment_requests():
    if not current_user.is_admin():
        abort(403)

    requests = AssignmentRequest.query.filter_by(status='PENDING') \
        .order_by(AssignmentRequest.created_at.asc()) \
        .all()

    return render_template('admin/assignment_requests.html', requests=requests, now=datetime.utcnow())


@admin_bp.route('/assignment-requests/<int:req_id>/approve', methods=['POST'])
@role_required('admin')
def approve_assignment_request(req_id):

    req = AssignmentRequest.query.get_or_404(req_id)
    ticket = req.ticket

    # 🔒 HARD RACE-CONDITION GUARD
    if ticket.assigned_to is not None:
        abort(409)

    if ticket.status in ['RESOLVED', 'CLOSED']:
        flash("Cannot assign a resolved/closed ticket.", "error")
        return redirect(url_for('admin.assignment_requests'))

    # Assign ticket
    ticket.assigned_to = req.agent_id
    ticket.status = 'IN_PROGRESS'

    # Approve this request
    req.status = 'APPROVED'

    # Reject all other pending requests for same ticket
    AssignmentRequest.query.filter(
        AssignmentRequest.ticket_id == ticket.id,
        AssignmentRequest.id != req.id,
        AssignmentRequest.status == 'PENDING'
    ).update({'status': 'REJECTED'})

    db.session.commit()

    flash("Ticket assigned and moved to IN PROGRESS.", "success")
    return redirect(url_for('admin.assignment_requests'))



@admin_bp.route('/assignment-requests/<int:req_id>/reject', methods=['POST'])
@role_required('admin')
def reject_assignment_request(req_id):
    if not current_user.is_admin():
        abort(403)

    req = AssignmentRequest.query.get_or_404(req_id)

    if req.status != 'PENDING':
        flash("Request already processed.", "info")
        return redirect(url_for('admin.assignment_requests'))

    req.status = 'REJECTED'
    db.session.commit()

    flash('Assignment request rejected.', 'info')
    return redirect(url_for('admin.assignment_requests'))


