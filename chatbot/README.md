# 🤖 CampusBot – Chatbot Integration Guide

A fully-featured AI chatbot for your Campus Events Django project.  
Built with intent detection, event search, and session-based recommendations.

---

## 📁 Files Delivered

```
chatbot_output/
├── chatbot/
│   ├── __init__.py
│   ├── apps.py             ← Django app config
│   ├── views.py            ← Core chatbot logic + API endpoint
│   ├── urls.py             ← URL routing for /chatbot/api/chat/
│   └── sample_data.py      ← Script to populate test events
└── templates/
    └── chatbot/
        └── widget.html     ← Drop-in chatbot UI component
```

---

## 🚀 Step-by-Step Integration

### Step 1 — Copy the `chatbot/` folder into your project root

```
campus_events-main/
├── chatbot/          ← paste here (same level as events/, users/)
│   ├── __init__.py
│   ├── apps.py
│   ├── views.py
│   └── urls.py
├── events/
├── users/
└── manage.py
```

### Step 2 — Copy the template

Copy `templates/chatbot/widget.html` into your project's `templates/chatbot/` directory:

```
campus_events-main/templates/chatbot/widget.html
```

### Step 3 — Register the app in `settings.py`

Open `campus_events/settings.py` and add `'chatbot'` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    'chatbot',
]
```

### Step 4 — Add the URL route in `campus_events/urls.py`

```python
from django.urls import path, include

urlpatterns = [
    # ... existing URLs ...
    path('chatbot/', include('chatbot.urls')),   # ← add this line
]
```

### Step 5 — Include the widget in your base template

Open `templates/base.html` (or `templates/dashboard/student.html`) and add this tag just before `</body>`:

```html
    {% include "chatbot/widget.html" %}
  </body>
</html>
```

> ✅ The chatbot will now appear on **all pages** if added to `base.html`,  
> or only on the student dashboard if added to `student.html`.

### Step 6 — Run the server

```bash
cd campus_events-main
python manage.py runserver
```

Open http://127.0.0.1:8000/dashboard/student/ — you'll see the 🤖 button in the bottom-right corner!

### Step 7 (Optional) — Populate sample data

```bash
python manage.py shell < chatbot/sample_data.py
```

This creates 8 sample events across all categories so the chatbot has real data to return.

---

## 🏗️ How It Works

### Intent Detection (Keyword-based NLP)

The chatbot uses **regex-based intent patterns** in `views.py`:

```python
INTENT_PATTERNS = {
    "greeting":    r"\b(hi|hello|hey)\b",
    "list_events": r"\b(list|show|all events?|upcoming)\b",
    "category":    r"\b(technical|cultural|sports|workshop)\b",
    "recommend":   r"\b(recommend|suggest|for me)\b",
    # ... more patterns
}
```

No external NLP library needed — pure Python regex.

### Event Search

When the user mentions an event name or keyword, the API does:

```python
Event.objects.filter(
    status='approved'
).filter(
    Q(title__icontains=keyword) |
    Q(description__icontains=keyword) |
    Q(venue__icontains=keyword)
)
```

### Recommendation Engine

Recommendations are built from:
1. **Logged-in users**: looks at their past `Registration` records to find preferred categories
2. **Anonymous users**: uses `viewed_event_ids` (event IDs the page has in `data-event-id` attributes)
3. **Fallback**: returns the 5 nearest upcoming events

### Chat History

Session history is maintained **in-browser** (JavaScript array) — no server-side storage needed. This keeps it lightweight.

---

## 🗺️ Google Maps Integration

Event venues automatically get a Google Maps search link:

```python
map_url = f"https://www.google.com/maps/search/{venue}+campus"
```

The chatbot shows this link when a user asks "where is [event]?" or "directions to [event]".  
No API key required — uses the public Google Maps search URL.

---

## 📊 Database Schema (existing models used)

The chatbot reads from your existing `events_event` table:

| Field | Used For |
|-------|----------|
| `title` | Search, display |
| `description` | Search, detail view |
| `category` | Category filtering |
| `date` | Date filtering (today/week/month) |
| `start_time`, `end_time` | Timing display |
| `venue` | Location info + map link |
| `status` | Only `approved` events shown |
| `is_paid`, `registration_fee` | Fee display |
| `max_capacity` | Seats remaining |

No new database migrations needed! ✅

---

## 💬 Example Conversations

| User says | Bot does |
|-----------|----------|
| `hi` | Greets with feature overview |
| `show upcoming events` | Lists next 6 approved events |
| `technical events this week` | Filters by category + date |
| `tell me about hackathon` | Full detail card with venue, time, fee |
| `where is the seminar held?` | Asks for event name, then shows venue + map link |
| `how do I register?` | Static FAQ response |
| `recommend events for me` | Personalized list based on past registrations |
| `events today` | Filters to today's date |
| `how do I get my certificate?` | FAQ on certificates |

---

## 🔧 Customisation

### Add more FAQ answers

In `chatbot/views.py`, edit the `FAQS` dictionary:

```python
FAQS = {
    "hostel": "Hostel bookings are managed by the admin office...",
    "wifi":   "Campus WiFi SSID is CampusNet. Login with your roll number...",
    # ...
}
```

Then add the intent pattern:

```python
INTENT_PATTERNS["hostel"] = r"\b(hostel|accommodation|stay)\b"
```

### Track event views for better recommendations

Add `data-event-id="{{ event.pk }}"` to event cards in your templates:

```html
<div class="event-card" data-event-id="{{ event.pk }}">
  ...
</div>
```

The chatbot's JavaScript picks these up automatically.

---

## ✅ Checklist

- [ ] Copied `chatbot/` folder to project root
- [ ] Copied `templates/chatbot/widget.html`
- [ ] Added `'chatbot'` to `INSTALLED_APPS`
- [ ] Added `path('chatbot/', include('chatbot.urls'))` to main urls.py
- [ ] Added `{% include "chatbot/widget.html" %}` to base.html
- [ ] Ran `python manage.py runserver`
- [ ] (Optional) Ran sample data script

---

## 🛠️ Troubleshooting

**Chatbot button not appearing?**  
→ Make sure `{% include "chatbot/widget.html" %}` is inside `<body>` in your base template.

**API returns 403 Forbidden?**  
→ The widget sends the CSRF token automatically. If issues persist, ensure `django.middleware.csrf.CsrfViewMiddleware` is in `MIDDLEWARE`.

**No events returned?**  
→ Make sure events have `status='approved'`. Run the sample data script.

**Font not loading?**  
→ The widget imports Google Fonts (Outfit). Works with internet. For offline, remove the `@import` line in the widget CSS.
