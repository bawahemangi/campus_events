# 🎓 Campus Event Management System

A full-stack Django web application for managing college events, registrations, QR-based attendance, digital certificates, feedback, and analytics.

---

## 📁 Project Structure

```
campus_events/
├── campus_events/          # Django project config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── users/                  # Authentication & user profiles
│   ├── models.py           # CustomUser with roles
│   ├── views.py            # Login, register, profile, leaderboard
│   ├── forms.py            # Student & organizer registration forms
│   ├── urls.py
│   └── admin.py
│
├── events/                 # Core event management
│   ├── models.py           # Event, Registration, Feedback, Notification
│   ├── views.py            # Events, registration, QR, certificates
│   ├── dashboard_views.py  # Student / Organizer / Admin dashboards
│   ├── forms.py            # EventForm (with clash detection), FeedbackForm
│   ├── utils.py            # Email, PDF certificates, recommendations
│   ├── urls.py
│   ├── dashboard_urls.py
│   └── admin.py
│
├── templates/
│   ├── base.html           # Shared navbar, notifications, styles
│   ├── users/              # login, register, profile, leaderboard
│   ├── events/             # event_list, event_detail, create_event, scan_qr
│   └── dashboard/          # student, organizer, admin, analytics
│
├── static/                 # CSS / JS assets
├── media/                  # Uploaded posters, QR codes, certificates
├── seed_data.py            # Demo data seeder
├── requirements.txt
└── manage.py
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites

- Python 3.9+
- pip

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` includes:
- `Django>=4.2`
- `Pillow` — image handling (posters, profile pics)
- `qrcode[pil]` — QR code generation
- `reportlab` — PDF certificate generation

### 4. Run Migrations

```bash
python manage.py makemigrations users
python manage.py makemigrations events
python manage.py migrate
```

### 5. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

Or use the seeded admin: `admin / admin123`

### 6. Seed Sample Data

```bash
python seed_data.py
```

This creates:
- 1 Admin, 3 Organizers, 5 Students
- 8 Events (approved, pending, past)
- Registrations, attendance records, feedback

### 7. Run the Development Server

```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## 🔐 Demo Login Credentials

| Role       | Username        | Password   |
|------------|-----------------|------------|
| Admin      | `admin`         | `admin123` |
| Organizer  | `coding_club`   | `pass1234` |
| Organizer  | `cultural_club` | `pass1234` |
| Student    | `student1`      | `pass1234` |
| Student    | `student2`      | `pass1234` |

---

## 📧 Email Setup (Gmail SMTP)

Edit `campus_events/settings.py`:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'youremail@gmail.com'
EMAIL_HOST_PASSWORD = 'your-16-char-app-password'   # Gmail App Password
DEFAULT_FROM_EMAIL = 'Campus Events <youremail@gmail.com>'
```

**To get a Gmail App Password:**
1. Go to Google Account → Security
2. Enable 2-Step Verification
3. Under "App passwords", generate one for "Mail"

**For demo/testing (no real emails):**
```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```
Emails print to terminal instead.

---

## ✨ Feature Guide

### 👤 Authentication
- Role-based registration: Student and Organizer have separate sign-up forms
- Admin is created via Django shell or `createsuperuser`
- Login redirects to role-appropriate dashboard

### 🗂 Event Management
- Organizers create events with: title, description, category, date/time, venue, capacity, poster image
- Admin approves or rejects with a reason
- **Venue Clash Detection**: form validation prevents two events at the same venue overlapping in time

### 📋 Registration System
- Students register for approved upcoming events
- Seats Left shown dynamically (updated every 15s via JS polling `/events/<id>/seats/`)
- Students can cancel before the event day
- Registration is blocked when event is full or past

### 📱 QR Code Attendance
- Unique QR generated per registration on signup
- QR contains token: `CAMPUS_EVENT|<uuid>|<event_id>|<student_id>`
- Organizer opens `/events/<id>/scan/` — uses device camera via `html5-qrcode`
- Manual entry fallback if camera unavailable
- One-click manual mark from the attendance table

### 📜 Digital Certificates
- Auto-generated as styled PDF (ReportLab) when attendance is marked
- Delivered via email attachment
- Also downloadable from student dashboard
- Certificate design: Navy background, gold border, student name, event, date, organizer signature

### 📧 Email Notifications (4 types)
| Trigger | Email sent |
|---|---|
| Event registration | Confirmation + QR attachment |
| Attendance marked | Certificate + PDF attachment |
| Event approved | Notification to organizer |
| (Extendable) | Reminders via management command |

### ⭐ Feedback System
- Students who attended can rate 1–5 stars + comment
- Average rating shown on event cards and detail page
- One review per student per event

### 🧠 Recommendation Engine
- Looks at a student's past registration categories
- Suggests upcoming approved events in the same category
- Falls back to all upcoming events for new students

### 📊 Analytics (Admin)
- Registrations per category (doughnut chart)
- Monthly registration trend (line chart)
- Top 10 events by registrations (horizontal bar)
- Recent registrations table

### 🏆 Leaderboard
- Students earn **10 points** per attended event
- Ranked by total participation points
- Top 3 shown as gold/silver/bronze podium
- Students can see their own rank highlighted

### 🔔 Notifications
- In-app bell in navbar (polls every 30s)
- Notifications created for: registration, approval, rejection, certificate
- Click any notification to mark as read

---

## 🌐 URL Map

| URL | Description |
|---|---|
| `/` | Redirects to dashboard |
| `/users/login/` | Login page |
| `/users/register/student/` | Student registration |
| `/users/register/organizer/` | Organizer registration |
| `/users/profile/` | User profile |
| `/users/leaderboard/` | Leaderboard |
| `/users/manage/` | Admin: all users |
| `/events/` | Event listing + search |
| `/events/<id>/` | Event detail |
| `/events/<id>/register/` | Register for event |
| `/events/create/` | Organizer: create event |
| `/events/<id>/edit/` | Organizer: edit event |
| `/events/<id>/scan/` | Organizer: QR scanner |
| `/events/certificate/<id>/` | Download certificate |
| `/dashboard/` | Role-based redirect |
| `/dashboard/student/` | Student dashboard |
| `/dashboard/organizer/` | Organizer dashboard |
| `/dashboard/admin/` | Admin dashboard |
| `/dashboard/admin/analytics/` | Analytics page |
| `/dashboard/admin/approve/<id>/` | Approve event |
| `/dashboard/admin/reject/<id>/` | Reject event |

### API Endpoints (JSON)

| URL | Method | Description |
|---|---|---|
| `/events/<id>/seats/` | GET | Live seat count |
| `/events/notifications/` | GET | Unread notifications |
| `/events/notifications/<id>/read/` | POST | Mark notification read |
| `/events/attendance/mark/` | POST | Mark attendance via QR token |
| `/events/attendance/manual/<id>/` | GET | Manually mark attendance |

---

## 🛠 Extending the Project

### Add Event Reminders (cron job)
```python
# In events/management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from events.models import Registration
from events.utils import send_event_reminder
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        tomorrow = timezone.now().date() + timedelta(days=1)
        regs = Registration.objects.filter(event__date=tomorrow, attended=False)
        for reg in regs:
            send_event_reminder(reg)
        self.stdout.write(f"Sent {regs.count()} reminders")
```

Run daily: `python manage.py send_reminders`

### Deploy to Production
1. Set `DEBUG = False` in settings
2. Set a secure `SECRET_KEY`
3. Add your domain to `ALLOWED_HOSTS`
4. Run `python manage.py collectstatic`
5. Use Gunicorn + Nginx
6. Switch to PostgreSQL for production

---

## 🧪 Running Tests

```bash
python manage.py test
```

---

## 📸 Tech Stack Summary

| Layer | Technology |
|---|---|
| Backend | Django 4.2 (Python) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5, Chart.js, Vanilla JS |
| QR Codes | `qrcode[pil]` library |
| PDF Certificates | `reportlab` library |
| QR Scanning | `html5-qrcode` (browser camera API) |
| Email | Django SMTP / Gmail |
| Fonts | Syne + DM Sans (Google Fonts) |
| Icons | Font Awesome 6 |

---

*Built for college presentations — clean, modular, and fully functional.*
