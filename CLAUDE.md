# CLAUDE.md

This file provides guidance to AI assistants (including Claude) when working with this repository.

## Repository Overview

**Project:** Action Tracker — A weekly team action item tracking system with email ingestion.
**Framework:** Django 5.2 with SQLite
**Python:** 3.11+

The system captures action items for teams, categorizes them, assigns owners, and supports email-based ingestion via SendGrid/Mailgun inbound parse webhooks. It includes a web dashboard and automated weekly digest emails.

## Project Structure

```
/
├── CLAUDE.md                  # AI assistant guidance (this file)
├── manage.py                  # Django management entry point
├── requirements.txt           # Python dependencies
├── db.sqlite3                 # SQLite database (gitignored)
├── tracker/                   # Django project settings
│   ├── settings.py            # Configuration (env-var driven)
│   ├── urls.py                # Root URL routing
│   ├── wsgi.py
│   └── asgi.py
├── actions/                   # Core app: models, email parsing, webhook
│   ├── models.py              # Category, TeamMember, ActionItem, ActionResponse, InboundEmail
│   ├── email_parser.py        # Parses inbound emails into action items
│   ├── views.py               # Webhook endpoint for inbound email
│   ├── urls.py                # /api/email/inbound/
│   ├── admin.py               # Django admin configuration
│   └── management/commands/
│       ├── send_weekly_digest.py   # Email digest command
│       └── seed_demo_data.py       # Demo data seeder
├── dashboard/                 # Web UI app
│   ├── views.py               # Dashboard, detail, create, update, weekly report views
│   └── urls.py                # / (home), /action/<id>/, /report/<year>/week/<week>/
├── templates/
│   ├── base.html              # Base layout with navbar
│   ├── registration/login.html
│   ├── dashboard/             # Dashboard page templates
│   │   ├── home.html
│   │   ├── detail.html
│   │   ├── create.html
│   │   └── weekly_report.html
│   └── email/                 # Email digest templates
│       ├── weekly_digest.html
│       └── weekly_digest.txt
└── static/css/style.css       # All CSS styles
```

## Development Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data    # Creates admin user (admin/admin), sample categories, members, items
python manage.py runserver
```

## Build & Run Commands

- **Install dependencies:** `pip install -r requirements.txt`
- **Run migrations:** `python manage.py migrate`
- **Create migrations:** `python manage.py makemigrations actions`
- **Run dev server:** `python manage.py runserver`
- **Seed demo data:** `python manage.py seed_demo_data`
- **Send weekly digest:** `python manage.py send_weekly_digest`
- **Dry-run digest:** `python manage.py send_weekly_digest --dry-run`
- **Django system check:** `python manage.py check`
- **Create superuser:** `python manage.py createsuperuser`

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Dashboard home (requires login) |
| `/action/<id>/` | Action item detail view |
| `/action/create/` | Create new action item |
| `/action/<id>/update/` | Update action item (POST) |
| `/action/<id>/respond/` | Add response (POST) |
| `/report/<year>/week/<week>/` | Weekly report view |
| `/api/email/inbound/` | Inbound email webhook (POST, csrf-exempt) |
| `/admin/` | Django admin panel |
| `/login/` | Login page |

## Data Models

- **Category** — name, color (hex), description
- **TeamMember** — name, email, is_active
- **ActionItem** — title, description, status, priority, category (FK), owner (FK), due_date, week_number, year
- **ActionResponse** — linked to ActionItem, author (FK to TeamMember), body
- **InboundEmail** — raw log of all received emails, tracks processing status

### Action Item Statuses
`open`, `in_progress`, `blocked`, `completed`, `cancelled`

### Priority Levels
`low`, `medium`, `high`, `urgent`

## Email Ingestion

The system parses inbound emails at `/api/email/inbound/` (webhook endpoint). It supports both SendGrid and Mailgun inbound parse formats.

**How parsing works:**
- Lines starting with `- `, `* `, or numbered (`1. `) are extracted as individual action items
- `@name` assigns an owner by matching against TeamMember name/email
- `[Category]` or `#category` assigns a category
- Keywords like `urgent`, `asap`, `high priority` set priority
- Replies (via In-Reply-To header) are added as ActionResponse to existing items
- If no structured items are found, the email subject becomes a single action item

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | insecure dev key | Production secret key |
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts |
| `EMAIL_BACKEND` | console backend | `django.core.mail.backends.smtp.EmailBackend` for production |
| `EMAIL_HOST` | `smtp.sendgrid.net` | SMTP host |
| `SENDGRID_API_KEY` | (empty) | SendGrid API key |
| `DEFAULT_FROM_EMAIL` | `tracker@example.com` | Sender address |
| `INBOUND_EMAIL_WEBHOOK_SECRET` | (empty) | Shared secret for webhook verification |

## Code Style & Conventions

- **Language:** Python 3.11+
- **Framework:** Django 5.2 with function-based views
- **Naming:** snake_case for Python, BEM-like classes in CSS
- **Models:** defined in `actions/models.py`, all models use `ordering` in Meta
- **Views:** function-based with `@login_required` decorator for dashboard views
- **Templates:** Django template language, extending `base.html`
- **Admin:** all models registered with custom admin classes in `actions/admin.py`

## Important Notes for AI Assistants

- Read existing code before proposing modifications
- Keep changes minimal and focused on the task at hand
- Run `python manage.py check` after model changes
- Run `python manage.py makemigrations` after changing models
- The `actions` app handles data models and email processing; the `dashboard` app handles the web UI
- All dashboard views require authentication (`@login_required`)
- The webhook endpoint is csrf-exempt (for external email services) but supports signature verification
- Email backend defaults to console (prints to stdout) in development
