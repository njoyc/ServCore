# ServCore - Enterprise IT Ticket Management System

A production-grade, enterprise-ready ticket management system for internal IT support operations. Built with Flask, SQLAlchemy, and server-rendered templates for optimal performance and reliability.

## Overview

ServCore is a comprehensive ticket management platform similar to ServiceNow or Jira Service Desk, designed for enterprise organizations to manage IT, HR, and Operations support requests efficiently.

## Features

### Core Functionality

- **Ticket Management**: Create, view, update, and track support tickets
- **Comment System**: Discussion threads on each ticket
- **Workflow Management**: OPEN → IN_PROGRESS → RESOLVED → CLOSED
- **Role-Based Access Control**: User, Agent, and Admin roles with appropriate permissions
- **SLA Tracking**: Priority-based SLA targets with visual indicators
- **Assignment System**: Ticket assignment to agents with workload balancing

### User Roles

#### 1. User (Employee)

- Create new tickets
- View own tickets
- Add comments to own tickets
- Track ticket status and SLA

#### 2. Agent (Support Staff)

- View assigned tickets
- Pick up unassigned tickets
- Update ticket status
- Add resolution notes
- Manage ticket workflow

#### 3. Admin (Administrator)

- Full system access
- User management (CRUD)
- Ticket assignment interface
- Analytics dashboard with charts
- System-wide oversight

### Analytics & Reporting

- **Overview Statistics**: Total, open, closed, and resolved tickets
- **Visual Charts**: Status, priority, category distributions
- **Agent Performance**: Workload, resolution times, SLA compliance
- **Trend Analysis**: Resolution time trends over 30 days
- **Recent Activity Feed**: Latest ticket updates

### SLA Management

Priority-based SLA targets:

- **Critical**: 4 hours
- **High**: 24 hours
- **Medium**: 48 hours
- **Low**: 72 hours

Visual indicators show remaining time or overdue status with color coding (green/yellow/red).

## Technology Stack

- **Backend**: Flask 3.0 with Blueprints
- **Database**: SQLite (development) / PostgreSQL (production)
- **ORM**: SQLAlchemy 2.0
- **Authentication**: Flask-Login with session-based auth
- **Migrations**: Flask-Migrate
- **Frontend**: Server-rendered Jinja2 templates
- **Styling**: Custom CSS (no framework)
- **Charts**: Chart.js for analytics visualizations
- **JavaScript**: Vanilla JS (no frameworks)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment tool (venv)

### Setup Instructions

1. **Clone the repository**

```bash
git clone <repository-url>
cd servcore101
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set environment variables** (optional)

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**

```bash
# Database will be automatically created on first run
python run.py
```

The application will:

- Create the SQLite database (`dev.db`)
- Initialize tables
- Seed demo users

6. **Access the application**
   Open your browser and navigate to: `http://localhost:5000`

## Demo Credentials

The system comes pre-seeded with demo users for testing:

| Role  | Email              | Password |
| ----- | ------------------ | -------- |
| Admin | admin@example.com  | admin123 |
| Agent | agent1@example.com | agent123 |
| Agent | agent2@example.com | agent123 |
| User  | user1@example.com  | user123  |
| User  | user2@example.com  | user123  |
| User  | user3@example.com  | user123  |

## Project Structure

```
servcore101/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # Database models
│   ├── auth/                    # Authentication module
│   │   ├── __init__.py
│   │   ├── routes.py            # Login/logout routes
│   │   └── decorators.py        # Access control decorators
│   ├── main/                    # Main routes
│   │   ├── __init__.py
│   │   └── routes.py            # Dashboard routes
│   ├── tickets/                 # Ticket management
│   │   ├── __init__.py
│   │   ├── routes.py            # Ticket CRUD routes
│   │   └── services.py          # Business logic, SLA calculation
│   ├── admin/                   # Admin functionality
│   │   ├── __init__.py
│   │   ├── routes.py            # Admin routes
│   │   └── services.py          # Analytics queries
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html            # Base layout
│   │   ├── auth/                # Auth templates
│   │   ├── main/                # Dashboard templates
│   │   ├── tickets/             # Ticket templates
│   │   └── admin/               # Admin templates
│   └── static/                  # Static assets
│       ├── css/
│       │   └── style.css        # Main stylesheet
│       └── js/
│           └── main.js          # Client-side JavaScript
├── config.py                    # Configuration classes
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Configuration

### Development Configuration

```python
# config.py - DevelopmentConfig
DEBUG = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
```

### Production Configuration

```python
# config.py - ProductionConfig
DEBUG = False
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
SECRET_KEY = os.environ.get('SECRET_KEY')  # Required!
SESSION_COOKIE_SECURE = True
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost/servcore
```

## Database Schema

### Users Table

- id, name, email, password_hash, role, created_at
- Relationships: created_tickets, assigned_tickets, comments

### Tickets Table

- id, title, description, category, priority, status
- created_at, resolved_at, created_by, assigned_to
- Relationships: creator, assignee, comments

### Comments Table

- id, ticket_id, user_id, text, created_at
- Relationships: ticket, author

## Workflow & Business Logic

### Ticket Status Workflow

```
OPEN → IN_PROGRESS → RESOLVED → CLOSED
  ↑         ↓           ↑
  └─────────┴───────────┘
```

**Valid Transitions:**

- OPEN → IN_PROGRESS (Agent starts work)
- IN_PROGRESS → OPEN (Agent reopens)
- IN_PROGRESS → RESOLVED (Agent resolves)
- RESOLVED → IN_PROGRESS (Reopen if issue persists)
- RESOLVED → CLOSED (Admin closes, final state)

**Invalid Transitions:**

- OPEN → RESOLVED (must go through IN_PROGRESS)
- OPEN → CLOSED (must go through intermediate states)
- CLOSED → any state (final state, immutable)

### Access Control

**User Permissions:**

- Create tickets
- View only their own tickets
- Comment on their own tickets

**Agent Permissions:**

- View assigned tickets and unassigned tickets
- Pick up unassigned tickets
- Update ticket status
- Assign tickets
- Comment on accessible tickets

**Admin Permissions:**

- Full access to all tickets
- User management (create, edit, delete)
- Ticket assignment
- Close tickets (final state)
- Access analytics dashboard

## API Endpoints

### Authentication

- `GET /login` - Login page
- `POST /login` - Process login
- `GET /logout` - Logout

### Main Routes

- `GET /` - Home (redirects to dashboard)
- `GET /dashboard` - User dashboard
- `GET /agent/dashboard` - Agent dashboard

### Ticket Routes

- `GET /tickets` - List tickets
- `GET /tickets/create` - Create ticket form
- `POST /tickets/create` - Create ticket
- `GET /tickets/<id>` - View ticket detail
- `POST /tickets/<id>/comment` - Add comment
- `POST /tickets/<id>/status` - Update status
- `POST /tickets/<id>/assign` - Assign ticket
- `POST /tickets/<id>/pickup` - Agent picks up ticket

### Admin Routes

- `GET /admin/dashboard` - Analytics dashboard
- `GET /admin/users` - User list
- `GET /admin/users/create` - Create user form
- `POST /admin/users/create` - Create user
- `GET /admin/users/<id>/edit` - Edit user form
- `POST /admin/users/<id>/edit` - Update user
- `POST /admin/users/<id>/delete` - Delete user
- `GET /admin/assign` - Assignment interface
- `POST /admin/assign/<ticket_id>` - Assign ticket

## Security Features

- **Password Hashing**: PBKDF2-SHA256 via Werkzeug
- **Session Security**: HttpOnly, Secure (production), SameSite cookies
- **CSRF Protection**: Built-in Flask protection
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **XSS Prevention**: Jinja2 auto-escaping
- **Access Control**: Route-level decorators enforce permissions

## Deployment

### Production Deployment Checklist

1. **Set SECRET_KEY**

   ```bash
   export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
   ```

2. **Configure PostgreSQL**

   ```bash
   export DATABASE_URL=postgresql://user:password@host:port/database
   ```

3. **Set production environment**

   ```bash
   export FLASK_ENV=production
   ```

4. **Initialize database**

   ```bash
   flask db upgrade  # If using migrations
   # Or python run.py to auto-create tables
   ```

5. **Use production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
   ```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:create_app('production')"]
```

## Database Migration to PostgreSQL

The schema is PostgreSQL-compatible. To migrate:

1. **Export SQLite data** (if needed)
2. **Update DATABASE_URL** to PostgreSQL connection string
3. **Run application** - tables will be created automatically
4. **Import data** (if migrating from SQLite)

## Testing

### Manual Testing Checklist

**Authentication:**

- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Logout

**User Journey:**

- [ ] Create ticket
- [ ] View own tickets
- [ ] Add comment
- [ ] Cannot view others' tickets

**Agent Journey:**

- [ ] View assigned tickets
- [ ] Pick up unassigned ticket
- [ ] Update ticket status
- [ ] View SLA indicators

**Admin Journey:**

- [ ] Create user
- [ ] Edit user
- [ ] Delete user
- [ ] Assign tickets
- [ ] View analytics dashboard

**Workflow:**

- [ ] OPEN → IN_PROGRESS transition
- [ ] IN_PROGRESS → RESOLVED transition
- [ ] RESOLVED → CLOSED transition
- [ ] Invalid transitions blocked

## Troubleshooting

### Database Issues

```bash
# Reset database
rm dev.db
python run.py
```

### Import Errors

```bash
# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

### Port Already in Use

```bash
# Change port in run.py
app.run(host='0.0.0.0', port=5001)
```

## Future Enhancements

- Email notifications
- File attachments
- Advanced search and filtering
- Ticket templates
- Knowledge base integration
- Mobile responsive design improvements
- API endpoints for integrations
- Automated testing suite

## License

This project is for enterprise internal use.

## Support

For issues or questions, please contact your system administrator.

---
