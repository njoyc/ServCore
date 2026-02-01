import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import config

# ===============================
# Extensions
# ===============================
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def create_app(config_name=None):
    """
    Flask application factory
    """

    # Resolve config name safely
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)

    # Ensure instance folder exists (for SQLite, uploads, etc.)
    os.makedirs(app.instance_path, exist_ok=True)

    # Load configuration
    app.config.from_object(config[config_name])

    # Run production-only checks if defined
    if hasattr(config[config_name], "init_app"):
        config[config_name].init_app(app)

    # ===============================
    # Initialize extensions
    # ===============================
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page"
    login_manager.session_protection = "strong"

    # ===============================
    # User loader
    # ===============================
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ===============================
    # Register blueprints
    # ===============================
    from app.auth import auth_bp
    from app.main import main_bp
    from app.tickets import tickets_bp
    from app.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tickets_bp, url_prefix="/tickets")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # ===============================
    # Jinja globals
    # ===============================
    from app.services.sla_service import calculate_sla_status
    app.jinja_env.globals["calculate_sla_status"] = calculate_sla_status

    # ===============================
    # DB init (DEV ONLY)
    # ===============================
    if config_name != "production":
        with app.app_context():
            db.create_all()
            init_db()

    return app


def init_db():
    """
    Seed database with initial users (DEV ONLY)
    """
    from app.models import User

    # Do not reseed if admin already exists
    if User.query.filter_by(email="admin@example.com").first():
        return

    admin = User(name="Admin User", email="admin@example.com", role="admin")
    admin.set_password("admin123")

    agent1 = User(name="Agent One", email="agent1@example.com", role="agent")
    agent1.set_password("agent123")

    agent2 = User(name="Agent Two", email="agent2@example.com", role="agent")
    agent2.set_password("agent123")

    user1 = User(name="John Doe", email="user1@example.com", role="user")
    user1.set_password("user123")

    user2 = User(name="Jane Smith", email="user2@example.com", role="user")
    user2.set_password("user123")

    user3 = User(name="Bob Johnson", email="user3@example.com", role="user")
    user3.set_password("user123")

    db.session.add_all([admin, agent1, agent2, user1, user2, user3])
    db.session.commit()

    print("✔ Database seeded with default users")
