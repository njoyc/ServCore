from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import auth_bp
from app.models import User
from app import db


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # Redirect if already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Validation
        errors = {}
        if not email:
            errors['email'] = 'Email is required'
        if not password:
            errors['password'] = 'Password is required'
        elif len(password) < 6:
            errors['password'] = 'Password must be at least 6 characters'

        if errors:
            return render_template('auth/login.html', errors=errors, email=email)

        # Query user by email
        user = User.query.filter_by(email=email).first()

        # Verify credentials
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html', email=email)

        # Log in user
        login_user(user, remember=True)
        flash(f'Welcome back, {user.name}', 'success')

        # Redirect based on role
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif user.is_agent():
            return redirect(url_for('main.agent_dashboard'))
        else:
            return redirect(url_for('main.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))
