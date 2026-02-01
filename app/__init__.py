from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config
import os


# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name='default'):
    if not config_name:
        config_name = os.getenv('FLASK_ENV', 'development')
    """
    Flask application factory

    Args:
        config_name: Configuration name ('development', 'production', or 'default')

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    os.makedirs(app.instance_path, exist_ok=True)

    # Load configuration
    app.config.from_object(config[config_name])
    # Run production checks only if defined
    config[config_name].init_app(app) if hasattr(config[config_name], "init_app") else None


    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page'
    login_manager.session_protection = 'strong'

    # Import models for Flask-Login user loader
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.tickets import tickets_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Create database tables and seed data if needed
    with app.app_context():
        db.create_all()
        init_db()
	    # Register SLA helper into Jinja
    from app.services.sla_service import calculate_sla_status
    app.jinja_env.globals['calculate_sla_status'] = calculate_sla_status

    return app


def init_db():
    """Initialize database with seed data if empty"""
    from app.models import User

    # Check if admin user exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if admin:
        return  # Database already initialized

    # Create seed users
    admin_user = User(name='Admin User', email='admin@example.com', role='admin')
    admin_user.set_password('admin123')

    agent1 = User(name='Agent One', email='agent1@example.com', role='agent')
    agent1.set_password('agent123')

    agent2 = User(name='Agent Two', email='agent2@example.com', role='agent')
    agent2.set_password('agent123')

    user1 = User(name='John Doe', email='user1@example.com', role='user')
    user1.set_password('user123')

    user2 = User(name='Jane Smith', email='user2@example.com', role='user')
    user2.set_password('user123')

    user3 = User(name='Bob Johnson', email='user3@example.com', role='user')
    user3.set_password('user123')

    db.session.add_all([admin_user, agent1, agent2, user1, user2, user3])
    db.session.commit()

    print("Database initialized with seed users")

