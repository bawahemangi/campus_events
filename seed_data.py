"""
Seed script — creates demo users and events for testing.
Run: python manage.py shell < seed_data.py
OR:  python seed_data.py (if DJANGO_SETTINGS_MODULE is set)
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_events.settings')
django.setup()

from django.utils import timezone
from datetime import date, time, timedelta
from users.models import CustomUser
from events.models import Event, Registration, Feedback
from events.utils import create_notification

print("🌱 Seeding database...")

# ── Users ──────────────────────────────────────────────────────────────
def get_or_create_user(username, first, last, email, role, dept, password, **extra):
    if CustomUser.objects.filter(username=username).exists():
        print(f"  ↳ Skipping {username} (exists)")
        return CustomUser.objects.get(username=username)
    user = CustomUser(
        username=username, first_name=first, last_name=last,
        email=email, role=role, department=dept, **extra
    )
    user.set_password(password)
    user.save()
    print(f"  ✅ Created {role}: {username}")
    return user

admin   = get_or_create_user('admin',    'Admin',   'User',    'admin@campus.edu',      'admin',     'Administration', 'admin123')
org1    = get_or_create_user('coding_club','Arjun',  'Mehta',   'arjun@campus.edu',      'organizer', 'Coding Club',    'pass1234')
org2    = get_or_create_user('cultural_club','Priya','Sharma',  'priya@campus.edu',      'organizer', 'Cultural Club',  'pass1234')
org3    = get_or_create_user('sports_club', 'Rahul', 'Verma',   'rahul@campus.edu',      'organizer', 'Sports Club',    'pass1234')
s1      = get_or_create_user('student1',  'Ananya',  'Gupta',   'ananya@campus.edu',     'student',   'CSE',            'pass1234', roll_number='CS21001', year_of_study=3)
s2      = get_or_create_user('student2',  'Vikram',  'Singh',   'vikram@campus.edu',     'student',   'ECE',            'pass1234', roll_number='EC21045', year_of_study=2)
s3      = get_or_create_user('student3',  'Meera',   'Patel',   'meera@campus.edu',      'student',   'Mechanical',     'pass1234', roll_number='ME21023', year_of_study=4)
s4      = get_or_create_user('student4',  'Rohan',   'Kumar',   'rohan@campus.edu',      'student',   'Civil',          'pass1234', roll_number='CV21067', year_of_study=1)
s5      = get_or_create_user('student5',  'Sneha',   'Nair',    'sneha@campus.edu',      'student',   'CSE',            'pass1234', roll_number='CS21099', year_of_study=3)

today = timezone.now().date()

# ── Events ─────────────────────────────────────────────────────────────
def create_event(title, desc, cat, organizer, days_ahead, start_h, end_h, venue, cap, status='approved'):
    if Event.objects.filter(title=title).exists():
        print(f"  ↳ Skipping event: {title}")
        return Event.objects.get(title=title)
    e = Event.objects.create(
        title=title, description=desc, category=cat,
        organizer=organizer,
        date=today + timedelta(days=days_ahead),
        start_time=time(start_h, 0), end_time=time(end_h, 0),
        venue=venue, max_capacity=cap, status=status
    )
    print(f"  ✅ Created event: {title} ({status})")
    return e

e1 = create_event(
    'HackFest 2024',
    'Annual 24-hour hackathon. Build innovative solutions using AI/ML and win exciting prizes! Open to all departments.',
    'technical', org1, 7, 9, 21, 'Innovation Lab, Block A', 80
)
e2 = create_event(
    'Annual Cultural Night',
    'A spectacular evening of music, dance, drama and art. Performances by students from all departments.',
    'cultural', org2, 14, 17, 21, 'Main Auditorium', 500
)
e3 = create_event(
    'Intra-College Cricket Tournament',
    'Departmental cricket tournament. Teams of 11 players. Round-robin format followed by knockout rounds.',
    'sports', org3, 3, 8, 17, 'College Cricket Ground', 150
)
e4 = create_event(
    'Python & Machine Learning Workshop',
    'Hands-on 2-day workshop covering NumPy, Pandas, Scikit-learn and building your first ML model.',
    'workshop', org1, 21, 10, 16, 'CS Lab 201', 40
)
e5 = create_event(
    'Entrepreneurship Summit',
    'Industry leaders share their journeys. Panel discussion, networking session and pitching competition.',
    'seminar', org2, 10, 10, 14, 'Seminar Hall B', 200
)
# Past events
e6 = create_event(
    'Web Dev Bootcamp',
    'Full-stack web development bootcamp covering HTML, CSS, React, Node.js and deployment.',
    'workshop', org1, -10, 10, 17, 'CS Lab 101', 50
)
e7 = create_event(
    'Fresher\'s Welcome 2024',
    'Grand welcome party for freshers! Games, music, food, and introductions to all college clubs.',
    'cultural', org2, -5, 16, 21, 'Open Air Theatre', 400
)
# Pending event
e8 = create_event(
    'Robotics Challenge',
    'Design, build and compete with your robots in obstacle courses and battle arenas.',
    'technical', org1, 30, 9, 17, 'Workshop Area, Block C', 60, status='pending'
)

# ── Registrations for past events ──────────────────────────────────────
def register_attend(student, event, attended=True):
    reg, created = Registration.objects.get_or_create(student=student, event=event)
    if created:
        reg.generate_qr_code()
        reg.save()
    if attended and not reg.attended:
        reg.mark_attended()
    return reg

print("\n📝 Creating registrations...")
register_attend(s1, e6, attended=True)
register_attend(s2, e6, attended=True)
register_attend(s3, e6, attended=False)
register_attend(s1, e7, attended=True)
register_attend(s2, e7, attended=True)
register_attend(s4, e7, attended=True)
register_attend(s5, e7, attended=False)

# Future event registrations
for student in [s1, s2, s3, s4]:
    reg, created = Registration.objects.get_or_create(student=student, event=e1)
    if created:
        reg.generate_qr_code()
        reg.save()
        print(f"  ✅ Registered {student.username} for {e1.title}")

for student in [s1, s3, s5]:
    reg, created = Registration.objects.get_or_create(student=student, event=e2)
    if created:
        reg.generate_qr_code()
        reg.save()

# ── Feedback ──────────────────────────────────────────────────────────
print("\n⭐ Creating feedback...")
feedback_data = [
    (s1, e6, 5, "Amazing workshop! Learned so much about React."),
    (s2, e6, 4, "Good content but could use more hands-on time."),
    (s1, e7, 5, "Best cultural night ever! Great performances."),
    (s2, e7, 4, "Loved the dance performances. Food was great too!"),
    (s4, e7, 5, "Incredible event organization. Will definitely attend next year!"),
]
for student, event, rating, comment in feedback_data:
    if not Feedback.objects.filter(student=student, event=event).exists():
        Feedback.objects.create(student=student, event=event, rating=rating, comment=comment)
        print(f"  ✅ Feedback: {student.username} → {event.title} ({rating}★)")

# ── Notifications ─────────────────────────────────────────────────────
print("\n🔔 Creating sample notifications...")
create_notification(s1, 'Welcome to CampusEvents!', 'Browse and register for upcoming events.', 'general')
create_notification(org1, 'HackFest 2024 is LIVE!', 'Your event has been approved and is now visible to all students.', 'approval')

print("\n✅ Database seeded successfully!")
print("\n📋 Login credentials:")
print("   Admin:     admin / admin123")
print("   Organizer: coding_club / pass1234")
print("   Organizer: cultural_club / pass1234")
print("   Student:   student1 / pass1234")
print("   Student:   student2 / pass1234")
