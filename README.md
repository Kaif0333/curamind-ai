# CuraMind AI - Appointment Management System

## Project Overview
CuraMind AI is a Django-based healthcare appointment management system with role-based access for patients and doctors.

## Features
- Custom User model (Doctor / Patient)
- Secure authentication and login
- Patient appointment booking
- Doctor approval / rejection workflow
- Appointment status tracking
- Email notifications on approval / rejection
- Bootstrap-based UI
- Admin panel for full control
- Environment variable security using `.env`
- Patient self-registration
- Interactive API docs
- Demo data seeding command

## Tech Stack
- Python
- Django
- SQLite
- Bootstrap
- Gmail SMTP

## Installation Steps
1. Clone repository
```bash
git clone <repo-url>
cd curamind_ai
```

2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Setup environment variables
Create a `.env` file:
```bash
EMAIL_HOST_USER=yourgmail@gmail.com
EMAIL_HOST_PASSWORD=yourapppassword
DJANGO_SECRET_KEY=replace-this-with-a-strong-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
```

5. Run migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser
```bash
python manage.py createsuperuser
```

7. Run server
```bash
python manage.py runserver
```

8. Seed demo users and appointments (optional)
```bash
python manage.py seed_demo
```

## Running This Project (Important)
This repository is a Django project, not a FastAPI `app.main` layout.

Use one of these commands from the project root:
```bash
venv\Scripts\python.exe manage.py runserver
```

If you want ASGI with Uvicorn, run:
```bash
venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Useful URLs
- `/` - Home page
- `/accounts/register/` - Patient registration
- `/accounts/login/` - Login
- `/admin/` - Admin panel
- `/docs/` - Interactive API docs (Swagger UI)
- `/routes/` - Quick route index

## Settings Modules
- Development: `config.settings_dev`
- Production: `config.settings_prod`
- Default (current): `config.settings`

## Deployment (Render)
This project is now deployment-ready for Render.

1. Push code to GitHub
2. In Render, create a new `Web Service` from this repo
3. Use:
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn config.wsgi:application --log-file -`
4. Set environment variables:
   - `DJANGO_ENV=production`
   - `DEBUG=False`
   - `DJANGO_SECRET_KEY=<strong-random-secret>`
   - `ALLOWED_HOSTS=<your-render-domain>`
   - `CSRF_TRUSTED_ORIGINS=https://<your-render-domain>`
   - `DATABASE_URL=<managed-postgres-url>` (recommended)
   - `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` (optional for email notifications)

You can also deploy with `render.yaml` included in this repository.

## User Roles
- Patient: Book appointments and track status
- Doctor: Approve or reject appointments
- Admin: Full system control
