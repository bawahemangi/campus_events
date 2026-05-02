"""
Sample data for Campus Events Chatbot testing.
Run: python manage.py shell < chatbot/sample_data.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'campus_events.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from events.models import Event
from datetime import date, timedelta, time

User = get_user_model()

# ── Create organizer user if needed ────────────────────────────────────────
organizer, _ = User.objects.get_or_create(
    username='organizer1',
    defaults={
        'email': 'organizer@campus.edu',
        'role': 'organizer',
        'first_name': 'Events',
        'last_name': 'Team',
    }
)
if _:
    organizer.set_password('organizer123')
    organizer.save()
    print("✅ Organizer user created: organizer1 / organizer123")

today = date.today()

# ── Sample events ───────────────────────────────────────────────────────────
sample_events = [
    {
        "title": "National Hackathon 2025",
        "description": (
            "A 24-hour hackathon where students build innovative tech solutions. "
            "Teams of 2–4 members compete for prizes worth ₹1,00,000. "
            "Theme: AI for Social Good. Open to all engineering students. "
            "Mentors from top tech companies will be present throughout."
        ),
        "category": "technical",
        "date": today + timedelta(days=5),
        "start_time": time(9, 0),
        "end_time": time(9, 0),    # next day – simplified
        "venue": "Main Auditorium, Block A",
        "max_capacity": 200,
        "status": "approved",
        "is_paid": True,
        "registration_fee": 199,
    },
    {
        "title": "Cultural Fest – Rhythm 2025",
        "description": (
            "Annual cultural extravaganza featuring music, dance, drama, and art competitions. "
            "Events include solo singing, group dance, stand-up comedy, fashion show, and painting contest. "
            "Cash prizes and certificates for winners. Celebrity performance on the final day!"
        ),
        "category": "cultural",
        "date": today + timedelta(days=12),
        "start_time": time(10, 0),
        "end_time": time(21, 0),
        "venue": "Open Air Theatre, Campus Ground",
        "max_capacity": 1000,
        "status": "approved",
        "is_paid": False,
        "registration_fee": 0,
    },
    {
        "title": "Python & Machine Learning Workshop",
        "description": (
            "Hands-on workshop covering Python fundamentals, data analysis with Pandas, "
            "and an introduction to Machine Learning using scikit-learn. "
            "Bring your laptop! Prerequisites: Basic programming knowledge. "
            "Certificate of completion provided to all attendees."
        ),
        "category": "workshop",
        "date": today + timedelta(days=3),
        "start_time": time(10, 0),
        "end_time": time(17, 0),
        "venue": "Computer Lab 3, Block C",
        "max_capacity": 40,
        "status": "approved",
        "is_paid": True,
        "registration_fee": 99,
    },
    {
        "title": "Inter-College Cricket Tournament",
        "description": (
            "Annual cricket tournament with 16 college teams competing for the championship trophy. "
            "T20 format matches played across 3 days. "
            "Registration open for both players and spectators. Refreshments provided."
        ),
        "category": "sports",
        "date": today + timedelta(days=8),
        "start_time": time(8, 0),
        "end_time": time(18, 0),
        "venue": "College Cricket Ground, Sports Complex",
        "max_capacity": 500,
        "status": "approved",
        "is_paid": False,
        "registration_fee": 0,
    },
    {
        "title": "Career Development Seminar",
        "description": (
            "Industry experts from Google, Infosys, and TCS will share insights on "
            "career planning, resume building, and interview preparation. "
            "Panel discussion followed by Q&A session. "
            "Great opportunity to network with professionals. Lunch provided."
        ),
        "category": "seminar",
        "date": today + timedelta(days=1),
        "start_time": time(11, 0),
        "end_time": time(16, 0),
        "venue": "Seminar Hall 1, Admin Block",
        "max_capacity": 150,
        "status": "approved",
        "is_paid": False,
        "registration_fee": 0,
    },
    {
        "title": "Web Development Bootcamp",
        "description": (
            "3-day intensive bootcamp covering HTML, CSS, JavaScript, React, and Django. "
            "Build a full-stack web application by the end of the bootcamp. "
            "Batch size limited to 30 students. Certificate provided. "
            "Prior programming experience preferred but not required."
        ),
        "category": "workshop",
        "date": today + timedelta(days=15),
        "start_time": time(9, 0),
        "end_time": time(18, 0),
        "venue": "Computer Lab 1, Block C",
        "max_capacity": 30,
        "status": "approved",
        "is_paid": True,
        "registration_fee": 299,
    },
    {
        "title": "Freshers' Welcome Party",
        "description": (
            "Welcome party for new students! Fun activities, introductions, games, and cultural performances. "
            "Great opportunity to make new friends and learn about campus life. "
            "Free food and refreshments. Dress code: Casual."
        ),
        "category": "cultural",
        "date": today + timedelta(days=2),
        "start_time": time(18, 0),
        "end_time": time(22, 0),
        "venue": "Student Activity Centre",
        "max_capacity": 300,
        "status": "approved",
        "is_paid": False,
        "registration_fee": 0,
    },
    {
        "title": "Yoga & Mindfulness Session",
        "description": (
            "Start your wellness journey with certified yoga instructors. "
            "Morning session covering breathing techniques, asanas, and meditation. "
            "Suitable for beginners. Bring a yoga mat. "
            "Regular sessions every Saturday – this is the launch event."
        ),
        "category": "sports",
        "date": today,
        "start_time": time(6, 30),
        "end_time": time(8, 0),
        "venue": "Garden Area, Behind Library",
        "max_capacity": 50,
        "status": "approved",
        "is_paid": False,
        "registration_fee": 0,
    },
]

created = 0
for ev_data in sample_events:
    ev, created_flag = Event.objects.get_or_create(
        title=ev_data["title"],
        defaults={**ev_data, "organizer": organizer}
    )
    if created_flag:
        created += 1
        print(f"  ✅ Created: {ev.title}")
    else:
        print(f"  ⏭️  Already exists: {ev.title}")

print(f"\n🎉 Done! Created {created} new event(s). Total events: {Event.objects.count()}")