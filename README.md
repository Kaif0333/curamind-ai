# CuraMind AI – Appointment Management System

## Project Overview
CuraMind AI is a Django-based healthcare appointment management system with role-based access for patients and doctors.

## Features
- Custom User model (Doctor / Patient)
- Secure authentication & login
- Patient appointment booking
- Doctor approval / rejection workflow
- Appointment status tracking
- Email notifications on approval/rejection
- Bootstrap-based UI
- Admin panel for full control
- Environment variable security using .env

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
Create ```bash .env `` file:
```bash
EMAIL_HOST_USER=yourgmail@gmail.com
EMAIL_HOST_PASSWORD=yourapppassword
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
User Roles

Patient: Book appointments & track status

Doctor: Approve or reject appointments

Admin: Full system control

Author

S Mohammed Kaif Basha

Python Developer Intern – Zaalima Development