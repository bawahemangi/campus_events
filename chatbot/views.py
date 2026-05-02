"""
Campus Events Chatbot - Backend API
Handles intent detection, event search, and recommendations.
"""
import json
import re
from datetime import date, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from events.models import Event, Registration


# ─────────────────────────────────────────────────────────────────────────────
# FAQ / Static responses
# ─────────────────────────────────────────────────────────────────────────────
FAQS = {
    "register": (
        "To register for an event:\n"
        "1. Browse to the **Events** page\n"
        "2. Click on the event you're interested in\n"
        "3. Hit the **Register** button\n"
        "4. For paid events, complete the payment via Razorpay\n"
        "You'll receive a confirmation email with your QR code! 🎟️"
    ),
    "cancel": (
        "To cancel a registration:\n"
        "1. Go to your **Student Dashboard**\n"
        "2. Find the event under *My Upcoming Events*\n"
        "3. Click **Cancel Registration**\n"
        "Note: Paid events may have a refund policy. Check event details."
    ),
    "certificate": (
        "Certificates are issued after you **attend** the event.\n"
        "Once marked as attended by the organizer:\n"
        "1. Go to your **Dashboard → Past Events**\n"
        "2. Click **Download Certificate** next to the event\n"
        "You can also get it emailed to you automatically! 🏅"
    ),
    "qr": (
        "Your **QR code** is generated after registration.\n"
        "Find it in your Dashboard under *My Upcoming Events*.\n"
        "Show it at the venue for quick attendance marking. 📱"
    ),
    "points": (
        "You earn **10 points** for every event you attend!\n"
        "Points contribute to your Leaderboard Rank.\n"
        "Check your current points on the **Student Dashboard**. 🏆"
    ),
    "leaderboard": (
        "The **Leaderboard** ranks students by participation points.\n"
        "Attend more events to climb the ranks!\n"
        "Each attended event = 10 points. 🌟"
    ),
    "categories": (
        "Events are organized into these categories:\n"
        "🖥️ **Technical** – Hackathons, coding contests, tech talks\n"
        "🎭 **Cultural** – Music, dance, drama, art\n"
        "🏆 **Sports** – Tournaments, fitness events\n"
        "🔧 **Workshop** – Hands-on learning sessions\n"
        "📚 **Seminar** – Guest lectures, panel discussions\n"
        "📌 **Other** – Miscellaneous campus events"
    ),
    "paid": (
        "Some events charge a registration fee.\n"
        "Payments are processed securely via **Razorpay**.\n"
        "You'll see the fee on the event detail page before registering. 💳"
    ),
    "notification": (
        "You receive notifications for:\n"
        "• Registration confirmations\n"
        "• Payment receipts\n"
        "• Event reminders (24 hours before)\n"
        "• Certificate availability\n"
        "Check the 🔔 bell icon in the navbar for alerts."
    ),
    "help": (
        "Here's what I can help you with:\n"
        "🔍 **Search events** – Ask about any event by name, category, or date\n"
        "📅 **Upcoming events** – 'What events are this week?'\n"
        "📍 **Venue info** – 'Where is [event name] held?'\n"
        "ℹ️ **How-to guides** – Registration, QR codes, certificates\n"
        "🎯 **Recommendations** – Based on your interests\n\n"
        "Just type your question naturally! 😊"
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# Intent Detection
# ─────────────────────────────────────────────────────────────────────────────
INTENT_PATTERNS = {
    "greeting":       r"^(hi|hello|hey|good morning|good evening|howdy|sup|hii+|helo|hellow)[\s!?.]*$",
    "help":           r"\b(help|what can you do|how does this work|guide|assist)\b",
    "list_events":    r"\b(list|show all|all events?|browse|available events?|upcoming events?)\b",
    "search_event":   r"\b(find|search|look for|looking for|tell me about|details? of|details? about|info about|information about)\b",
    "category":       r"\b(technical events?|cultural events?|sports events?|workshop events?|seminar events?|hackathon|coding events?|dance events?|music events?)\b",
    "today":          r"\b(today|tonight)\b",
    "this_week":      r"\b(this week|next 7 days)\b",
    "this_month":     r"\b(this month)\b",
    "venue":          r"\b(venue|where is|location of|place of|held at|map|directions? to)\b",
    "time":           r"\b(when is|start time|schedule of|timing of)\b",
    "register":       r"\b(how (do i|to) register|how (do i|to) sign up|how (do i|to) enroll|registration process)\b",
    "cancel":         r"\b(how (do i|to) cancel|cancel registration|withdraw|unregister)\b",
    "certificate":    r"\b(certificate|cert|credential)\b",
    "qr":             r"\b(qr|qr code|qrcode)\b",
    "points":         r"\b(points|participation points)\b",
    "leaderboard":    r"\b(leaderboard|ranking|top students?)\b",
    "recommend":      r"\b(recommend|suggest|for me|what should i attend|interested in)\b",
    "paid":           r"\b(paid event|registration fee|event cost|event price|is it free|free event)\b",
    "notification":   r"\b(notification|notify|alert|reminder)\b",
    "goodbye":        r"\b(bye|goodbye|see you|that'?s all|done chatting)\b",
    "thanks":         r"^(thanks?|thank you|thx|ty|ok thanks?|okay thanks?)[\s!.]*$",
    "deadline":       r"\b(deadline|last date|closing|expire|end date|due date)\b",
    "eligibility":    r"\b(eligible|eligibility|who can (join|apply|participate)|requirements?|criteria)\b",
    "contact":        r"\b(contact|reach out|organizer info|who is (in charge|conducting|organizing))\b",
    "refund":         r"\b(refund|money back|cancellation policy|return policy)\b",
    # Explicit event-interest triggers – user must clearly ask about events
    "show_upcoming":  r"\b(show (me )?(upcoming|next|new) events?|what events? are (there|available|coming|upcoming))\b",
    "events_today":   r"\b(events? today|what'?s? (on|happening) today)\b",
    "events_week":    r"\b(events? this week|what'?s? (on|happening) this week)\b",
}


def detect_intents(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, text_lower):
            found.append(intent)
    return found


def extract_event_name(text: str) -> str:
    """Extract a specific event name the user is asking about. Returns empty string if nothing meaningful found."""
    # Ignore short/common words that aren't event names
    STOP_WORDS = {
        "hi", "hey", "hello", "thanks", "thank", "ok", "okay", "sure", "yes", "no",
        "please", "help", "me", "you", "i", "we", "the", "a", "an", "is", "it",
        "what", "when", "where", "how", "who", "which", "any", "some", "all",
        "good", "great", "nice", "cool", "awesome"
    }
    # Require explicit search trigger words before extracting
    trigger = re.search(
        r'\b(tell me about|find|search for|show me|details? of|details? about|'
        r'info about|information about|where is|when is|about the)\b',
        text, flags=re.IGNORECASE
    )
    if not trigger:
        return ""  # No trigger = don't try to guess an event name

    # Extract what comes after the trigger phrase
    after = text[trigger.end():].strip()
    # Remove filler words at start
    after = re.sub(r'^(the|an?|event called|event named)\s+', '', after, flags=re.IGNORECASE).strip()
    words = [w for w in after.split() if w.lower() not in STOP_WORDS]
    result = " ".join(words).strip(" ?.!")
    return result if len(result) > 2 else ""


def get_date_filter(intents: list[str]):
    today = date.today()
    if "today" in intents:
        return today, today
    if "this_week" in intents:
        return today, today + timedelta(days=7)
    if "this_month" in intents:
        return today, today + timedelta(days=30)
    return today, None  # default: upcoming only


def get_category_filter(text: str):
    """Only match category if user explicitly asks about events in that category."""
    text_lower = text.lower()
    # Must have event-related word alongside the category keyword
    has_event_context = bool(re.search(
        r"\b(event|events?|show|list|find|search|upcoming|available|any)\b", text_lower
    ))
    if not has_event_context:
        return None
    mapping = {
        "technical": ["technical", "hackathon", "coding", "tech", "programming"],
        "cultural":  ["cultural", "dance", "music", "art", "drama"],
        "sports":    ["sports", "sport", "game", "tournament", "fitness"],
        "workshop":  ["workshop", "hands-on", "practical"],
        "seminar":   ["seminar", "lecture", "panel"],
    }
    for category, keywords in mapping.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Event Formatters
# ─────────────────────────────────────────────────────────────────────────────
def format_event_short(event: Event) -> str:
    fee = f"₹{event.registration_fee}" if event.is_paid else "Free"
    seats = f"{event.seats_left} seats left" if not event.is_full else "⚠️ Full"
    return (
        f"📌 **{event.title}**\n"
        f"   📅 {event.date.strftime('%b %d, %Y')} at {event.start_time.strftime('%I:%M %p')}\n"
        f"   📍 {event.venue}  |  🏷️ {event.get_category_display()}  |  💰 {fee}  |  {seats}"
    )


def format_event_detail(event: Event) -> str:
    fee = f"₹{event.registration_fee}" if event.is_paid else "Free"
    seats = f"{event.seats_left} seats left" if not event.is_full else "⚠️ Fully Booked"
    map_url = f"https://www.google.com/maps/search/{event.venue.replace(' ', '+')}+campus"
    return (
        f"**{event.title}**\n\n"
        f"📅 **Date:** {event.date.strftime('%B %d, %Y')}\n"
        f"⏰ **Time:** {event.start_time.strftime('%I:%M %p')} – {event.end_time.strftime('%I:%M %p')}\n"
        f"📍 **Venue:** {event.venue}\n"
        f"🗺️ **Map:** [View on Google Maps]({map_url})\n"
        f"🏷️ **Category:** {event.get_category_display()}\n"
        f"💰 **Fee:** {fee}\n"
        f"👥 **Capacity:** {seats}\n"
        f"⭐ **Rating:** {event.average_rating}/5\n\n"
        f"📝 **Description:**\n{event.description[:300]}{'...' if len(event.description) > 300 else ''}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────
def get_recommendations(user, viewed_ids: list[int]) -> list[Event]:
    """
    Basic recommendation:
    1. If user is authenticated, look at their past registrations for categories.
    2. Also consider session-viewed event IDs.
    3. Return upcoming events in those categories.
    """
    preferred_categories = set()
    today = date.today()

    if user and user.is_authenticated:
        past_regs = Registration.objects.filter(
            student=user
        ).select_related('event').order_by('-registered_at')[:10]
        for reg in past_regs:
            preferred_categories.add(reg.event.category)

    if viewed_ids:
        viewed_events = Event.objects.filter(id__in=viewed_ids)
        for ev in viewed_events:
            preferred_categories.add(ev.category)

    if preferred_categories:
        recs = Event.objects.filter(
            status='approved',
            date__gte=today,
            category__in=preferred_categories
        ).order_by('date')[:5]
        if recs.exists():
            return list(recs)

    # Fallback: return nearest upcoming events
    return list(Event.objects.filter(
        status='approved', date__gte=today
    ).order_by('date')[:5])


# ─────────────────────────────────────────────────────────────────────────────
# Main Chatbot Logic
# ─────────────────────────────────────────────────────────────────────────────
def build_response(user_message: str, user, viewed_ids: list[int]) -> str:
    text = user_message.strip()
    intents = detect_intents(text)
    today = date.today()

    # ── 1. Greeting – must respond with greeting only ──────────────────
    if "greeting" in intents:
        name = user.first_name if user and user.is_authenticated and user.first_name else "there"
        return (
            f"Hey {name}! 👋 I'm **CampusBot**, your campus events assistant.\n\n"
            "Here's what I can help you with:\n"
            "• 🔍 **Find events** – by name, category, or date\n"
            "• 📍 **Venue & timing** – details for any event\n"
            "• 🎯 **Recommendations** – based on your interests\n"
            "• ℹ️ **How-to help** – registration, QR codes, certificates\n\n"
            "What would you like to know? 😊"
        )

    # ── 2. Thanks / goodbye ────────────────────────────────────────────
    if "thanks" in intents or ("goodbye" in intents and len(intents) <= 2):
        return "You're welcome! 😊 Feel free to ask anytime. Good luck with your events! 🎉"

    # ── 3. Help ────────────────────────────────────────────────────────
    if "help" in intents and len(intents) <= 2:
        return FAQS["help"]

    # ── 4. FAQ intents (only when clearly asked, not as side-effects) ──
    FAQ_INTENTS = ["register", "cancel", "certificate", "qr", "points",
                   "leaderboard", "paid", "notification", "deadline", "eligibility", "contact", "refund"]
    for faq_key in FAQ_INTENTS:
        if faq_key in intents:
            # Don't trigger FAQ if user is clearly searching for an event
            if "search_event" not in intents and "list_events" not in intents:
                if faq_key in FAQS:
                    return FAQS[faq_key]
                elif faq_key == "deadline":
                    return "Most events close registrations **24 hours** before the start time. Check the specific event page for the exact deadline! ⏳"
                elif faq_key == "eligibility":
                    return "Eligibility varies by event. Generally, all current students can participate. Check the **'About'** section of the event for specific requirements. 🎓"
                elif faq_key == "contact":
                    return "You can find the organizer's contact details on the bottom of the event page. Feel free to reach out to them for specific queries! 📞"
                elif faq_key == "refund":
                    return "Refunds are processed if you cancel at least **48 hours** before the event. Please contact the administrator for any payment-related issues. 💳"

    # ── 5. Recommendations ────────────────────────────────────────────
    if "recommend" in intents:
        recs = get_recommendations(user, viewed_ids)
        if recs:
            lines = ["Here are some events you might enjoy! 🎯\n"]
            for ev in recs:
                lines.append(format_event_short(ev))
            lines.append("\nWant full details about any of these? Just ask!")
            return "\n\n".join(lines)
        return "No upcoming events found right now. Check back soon! 📅"

    # ── 6. Specific event search (user gave a name/keyword) ────────────
    keyword = extract_event_name(text)
    if keyword:
        events_qs = Event.objects.filter(
            status='approved'
        ).filter(
            Q(title__icontains=keyword) |
            Q(description__icontains=keyword) |
            Q(venue__icontains=keyword)
        ).order_by('date')[:5]

        if events_qs.count() == 1:
            return format_event_detail(events_qs.first())
        elif events_qs.count() > 1:
            lines = [f"Found **{events_qs.count()} events** matching \"{keyword}\":\n"]
            for ev in events_qs:
                lines.append(format_event_short(ev))
            lines.append("\nAsk about a specific one for full details! 👆")
            return "\n\n".join(lines)
        else:
            return (
                f"I couldn't find any events matching **\"{keyword}\"**. 🔍\n\n"
                "Try a shorter keyword, or ask me to **'show all events'** to browse everything."
            )

    # ── 7. Category listing (only when user explicitly asks) ───────────
    category = get_category_filter(text)
    date_from, date_to = get_date_filter(intents)

    wants_event_list = (
        category is not None
        or "list_events" in intents
        or "show_upcoming" in intents
        or "events_today" in intents
        or "events_week" in intents
        or any(i in intents for i in ["today", "this_week", "this_month"])
        and "event" in text.lower()   # only if they mentioned 'event'
    )

    if wants_event_list:
        events_qs = Event.objects.filter(status='approved', date__gte=date_from)
        if date_to:
            events_qs = events_qs.filter(date__lte=date_to)
        if category:
            events_qs = events_qs.filter(category=category)
        events_qs = events_qs.order_by('date')[:6]

        if events_qs.exists():
            if "events_today" in intents or "today" in intents:
                label = "today"
            elif "events_week" in intents or "this_week" in intents:
                label = "this week"
            elif "this_month" in intents:
                label = "this month"
            else:
                label = "upcoming"
            cat_label = f" in **{category.capitalize()}**" if category else ""
            lines = [f"Here are {label} events{cat_label}:\n"]
            for ev in events_qs:
                lines.append(format_event_short(ev))
            lines.append(f"\n_Showing {events_qs.count()} event(s). Ask about any one for full details!_")
            return "\n\n".join(lines)
        else:
            cat_msg = f" in **{category}**" if category else ""
            return f"No events found{cat_msg} for that period. Try asking for **'all upcoming events'**! 🔍"

    # ── 8. Venue/time question without a specific event name ───────────
    if "venue" in intents or "time" in intents:
        return (
            "Sure! Tell me which event you're asking about and I'll look it up.\n\n"
            "For example:\n"
            "• _\"Where is the Hackathon held?\"_\n"
            "• _\"When is the Cultural Fest?\"_"
        )

    # ── 9. True fallback – user said something unrecognised ───────────
    # Do NOT show events here. Just explain what the bot can do.
    return (
        "I didn't quite understand that. 🤔 Here's what you can ask me:\n\n"
        "• **'Show upcoming events'** – browse all events\n"
        "• **'Technical events'** – filter by category\n"
        "• **'Tell me about [event name]'** – get event details\n"
        "• **'Events today'** or **'events this week'** – by date\n"
        "• **'How do I register?'** – step-by-step help\n"
        "• **'Recommend events for me'** – personalised picks\n\n"
        "Just type your question naturally! 😊"
    )


# ─────────────────────────────────────────────────────────────────────────────
# API Endpoint
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_POST
def chatbot_api(request):
    try:
        body = json.loads(request.body)
        user_message = body.get("message", "").strip()
        viewed_ids = body.get("viewed_event_ids", [])  # IDs of events the user has browsed

        if not user_message:
            return JsonResponse({"error": "Empty message"}, status=400)

        user = request.user if request.user.is_authenticated else None
        response_text = build_response(user_message, user, viewed_ids)

        return JsonResponse({
            "reply": response_text,
            "timestamp": timezone.now().isoformat(),
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
