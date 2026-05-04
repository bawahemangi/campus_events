"""
Events app views - Event listing, detail, registration, QR, feedback,
+ New: ICS export (F2), Wishlist (F3), Gallery (F8), Q&A (F9), Team (F11), Search API (F5)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Count, Avg, Q
from .models import Event, Registration, Feedback, Notification, Wishlist, EventPhoto, EventQuestion, Team
from .forms import EventForm, FeedbackForm, EventSearchForm
from .utils import (
    send_registration_email, generate_certificate,
    send_certificate_email, create_notification, get_event_recommendations
)


def event_list(request):
    """Public event listing with search and filter."""
    form = EventSearchForm(request.GET)
    events = Event.objects.filter(status='approved')

    if form.is_valid():
        search = form.cleaned_data.get('search')
        category = form.cleaned_data.get('category')
        date_from = form.cleaned_data.get('date_from')
        date_to = form.cleaned_data.get('date_to')
        is_paid = form.cleaned_data.get('is_paid')
        sort_by = form.cleaned_data.get('sort_by')

        if search:
            events = events.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(venue__icontains=search)
            )
        if category:
            events = events.filter(category=category)
        if date_from:
            events = events.filter(date__gte=date_from)
        if date_to:
            events = events.filter(date__lte=date_to)
        if is_paid == 'paid':
            events = events.filter(is_paid=True)
        elif is_paid == 'free':
            events = events.filter(is_paid=False)

        if sort_by == 'popular':
            events = events.annotate(reg_count=Count('registrations')).order_by('-reg_count')
        elif sort_by == 'az':
            events = events.order_by('title')
        else:
            events = events.order_by('date')

    today = timezone.now().date()
    upcoming_events = events.filter(date__gte=today).order_by('date')
    past_events = events.filter(date__lt=today).order_by('-date')

    registered_ids = []
    wishlist_ids = []
    if request.user.is_authenticated:
        registered_ids = list(
            Registration.objects.filter(student=request.user)
            .values_list('event_id', flat=True)
        )
        wishlist_ids = list(
            Wishlist.objects.filter(user=request.user)
            .values_list('event_id', flat=True)
        )

    context = {
        'form': form,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'registered_ids': registered_ids,
        'wishlist_ids': wishlist_ids,
    }
    return render(request, 'events/event_list.html', context)


def event_search_api(request):
    """AJAX live search endpoint (F5)."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    today = timezone.now().date()
    events = Event.objects.filter(
        status='approved',
        date__gte=today
    ).filter(
        Q(title__icontains=q) | Q(venue__icontains=q) | Q(category__icontains=q)
    )[:8]

    results = [{
        'id': e.pk,
        'title': e.title,
        'date': e.date.strftime('%b %d, %Y'),
        'venue': e.venue,
        'category': e.get_category_display(),
        'seats_left': e.seats_left,
        'url': f'/events/{e.pk}/',
    } for e in events]
    return JsonResponse({'results': results})


def event_detail(request, pk):
    """Event detail page."""
    event = get_object_or_404(Event, pk=pk)

    if event.status != 'approved':
        if not request.user.is_authenticated:
            raise Http404
        if not (request.user == event.organizer or request.user.is_admin_user):
            raise Http404

    user_registration = None
    user_feedback = None
    feedback_form = None
    is_wishlisted = False
    user_team = None

    if request.user.is_authenticated:
        user_registration = Registration.objects.filter(
            event=event, student=request.user
        ).select_related('team').first()

        user_feedback = Feedback.objects.filter(
            event=event, student=request.user
        ).first()

        if user_registration and user_registration.attended and not user_feedback:
            feedback_form = FeedbackForm()

        is_wishlisted = Wishlist.objects.filter(user=request.user, event=event).exists()

        if user_registration and user_registration.team:
            user_team = user_registration.team

    feedbacks = event.feedbacks.select_related('student').order_by('-created_at')
    questions = event.questions.select_related('asker', 'answered_by').order_by('-created_at')
    photos = event.photos.all()[:12]

    context = {
        'event': event,
        'user_registration': user_registration,
        'user_feedback': user_feedback,
        'feedback_form': feedback_form,
        'feedbacks': feedbacks,
        'seats_left': event.seats_left,
        'is_wishlisted': is_wishlisted,
        'questions': questions,
        'photos': photos,
        'user_team': user_team,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def register_for_event(request, pk):
    """Register student for an event."""
    event = get_object_or_404(Event, pk=pk, status='approved')

    if not request.user.is_student:
        messages.error(request, 'Only students can register for events.')
        return redirect('event_detail', pk=pk)

    if event.is_full:
        messages.error(request, 'Sorry, this event is full!')
        return redirect('event_detail', pk=pk)

    if event.is_past:
        messages.error(request, 'Registration is closed for past events.')
        return redirect('event_detail', pk=pk)

    if Registration.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=pk)

    if event.team_event:
        messages.info(request, 'This is a team event. Please create or join a team to register.')
        return redirect('event_detail', pk=pk)

    if event.is_paid and event.registration_fee > 0:
        return redirect('initiate_payment', event_pk=pk)

    registration = Registration(event=event, student=request.user)
    registration.generate_qr_code()
    registration.save()

    send_registration_email(registration)
    create_notification(
        request.user,
        f'Registered: {event.title}',
        f'You have successfully registered for {event.title} on {event.date}.',
        'registration'
    )

    messages.success(request, f'Successfully registered for {event.title}! Check your email for QR code.')
    return redirect('event_detail', pk=pk)


@login_required
def cancel_registration(request, pk):
    """Cancel a registration."""
    registration = get_object_or_404(Registration, pk=pk, student=request.user)

    if registration.attended:
        messages.error(request, 'Cannot cancel after attendance is marked.')
        return redirect('event_detail', pk=registration.event.pk)

    event_title = registration.event.title
    registration.delete()
    messages.success(request, f'Registration for {event_title} cancelled.')
    return redirect('student_dashboard')


@login_required
def submit_feedback(request, pk):
    """Submit feedback for an event."""
    event = get_object_or_404(Event, pk=pk)

    registration = Registration.objects.filter(
        event=event, student=request.user, attended=True
    ).first()

    if not registration:
        messages.error(request, 'You can only give feedback for events you attended.')
        return redirect('event_detail', pk=pk)

    if Feedback.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You have already submitted feedback.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.event = event
            feedback.student = request.user
            feedback.save()
            messages.success(request, 'Thank you for your feedback!')

    return redirect('event_detail', pk=pk)


@login_required
def create_event(request):
    """Organizer creates a new event."""
    if not request.user.is_organizer:
        messages.error(request, 'Only organizers can create events.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.status = 'pending'
            event.save()
            messages.success(request,
                f'"{event.title}" submitted for admin approval! You will be notified once reviewed.')
            return redirect('organizer_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = field.replace('_', ' ').title() if field != '__all__' else 'Error'
                    messages.error(request, f'{label}: {error}')
    else:
        form = EventForm()

    return render(request, 'events/create_event.html', {
        'form': form,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def edit_event(request, pk):
    """Organizer edits an event."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.status = 'pending'
            updated.save()
            messages.success(request, f'"{updated.title}" updated and resubmitted for approval.')
            return redirect('organizer_dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = field.replace('_', ' ').title() if field != '__all__' else 'Error'
                    messages.error(request, f'{label}: {error}')
    else:
        form = EventForm(instance=event)

    return render(request, 'events/create_event.html', {
        'form': form,
        'event': event,
        'today': timezone.now().date().isoformat(),
    })


@login_required
def scan_qr(request, pk):
    """Organizer QR scan page for attendance."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    registrations = event.registrations.select_related('student').order_by('-registered_at')

    total = event.registered_count
    attended = event.attendance_count
    pct = round((attended / total * 100) if total else 0)
    circumference = 201
    pct_offset = circumference - (pct / 100) * circumference

    context = {
        'event':          event,
        'registrations':  registrations,
        'attended_count': attended,
        'total_count':    total,
        'pct_offset':     round(pct_offset, 1),
    }
    return render(request, 'events/scan_qr.html', context)


@login_required
def mark_attendance_api(request):
    """API endpoint to mark attendance via QR token."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    import json
    data = json.loads(request.body)
    token = data.get('token', '')

    try:
        registration = Registration.objects.select_related('student', 'event').get(qr_token=token)

        if registration.event.organizer != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})

        if registration.attended:
            return JsonResponse({
                'success': False,
                'already_marked': True,
                'message': f'{registration.student.get_full_name() or registration.student.username} already marked present.'
            })

        registration.mark_attended()
        generate_certificate(registration)
        send_certificate_email(registration)
        create_notification(
            registration.student,
            f'Attendance Marked: {registration.event.title}',
            f'Your attendance for {registration.event.title} has been marked. Check your email for your certificate!',
            'certificate'
        )

        return JsonResponse({
            'success': True,
            'message': f'Attendance marked for {registration.student.get_full_name() or registration.student.username}!',
            'student_name': registration.student.get_full_name() or registration.student.username,
            'registration_id': registration.pk,
        })

    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid QR code'})


@login_required
def mark_attendance_manual(request, registration_id):
    """Manually mark attendance from the list."""
    registration = get_object_or_404(Registration, pk=registration_id)

    if registration.event.organizer != request.user and not request.user.is_admin_user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})

    if not registration.attended:
        registration.mark_attended()
        generate_certificate(registration)
        send_certificate_email(registration)
        create_notification(
            registration.student,
            f'Attendance Marked: {registration.event.title}',
            f'Your attendance for {registration.event.title} has been marked. Check your email for your certificate!',
            'certificate'
        )

    return JsonResponse({
        'success': True,
        'attended': registration.attended,
        'student': registration.student.get_full_name() or registration.student.username
    })


@login_required
def download_certificate(request, registration_id):
    """Download certificate PDF."""
    registration = get_object_or_404(
        Registration, pk=registration_id, student=request.user, attended=True
    )

    if not registration.certificate:
        generate_certificate(registration)

    if registration.certificate and registration.certificate.path:
        with open(registration.certificate.path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="certificate_{registration.event.title}.pdf"'
            )
            return response

    messages.error(request, 'Certificate not available yet.')
    return redirect('student_dashboard')


@login_required
def seats_left_api(request, pk):
    """API: Return live seat count."""
    event = get_object_or_404(Event, pk=pk)
    return JsonResponse({
        'seats_left': event.seats_left,
        'is_full': event.is_full,
        'registered': event.registered_count,
        'max_capacity': event.max_capacity,
    })


@login_required
def notifications_api(request):
    """Get user notifications as JSON."""
    notifications = request.user.notifications.filter(is_read=False)[:10]
    data = [{
        'id': n.id,
        'title': n.title,
        'message': n.message,
        'type': n.notification_type,
        'link': n.link,
        'created_at': n.created_at.strftime('%b %d, %I:%M %p'),
    } for n in notifications]
    return JsonResponse({'notifications': data, 'count': len(data)})


@login_required
def mark_notification_read(request, pk):
    """Mark a notification as read."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
def all_notifications(request):
    """Full notifications page."""
    notifications = request.user.notifications.all()[:50]
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'events/notifications.html', {'notifications': notifications})


@login_required
def unmark_attendance(request, registration_id):
    """Undo attendance marking."""
    registration = get_object_or_404(Registration, pk=registration_id)

    if registration.event.organizer != request.user and not request.user.is_admin_user:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})

    if registration.attended:
        registration.attended = False
        registration.save()
        if registration.student.participation_points >= 10:
            registration.student.participation_points -= 10
            registration.student.save()

    return JsonResponse({
        'success': True,
        'student': registration.student.get_full_name() or registration.student.username
    })


def clash_check_api(request):
    """AJAX endpoint: check if an event would clash with existing ones."""
    date       = request.GET.get('date', '')
    start_time = request.GET.get('start_time', '')
    end_time   = request.GET.get('end_time', '')
    venue      = request.GET.get('venue', '').strip()
    exclude_id = request.GET.get('exclude_id', '')

    if not all([date, start_time, end_time, venue]):
        return JsonResponse({'clash': False})

    try:
        from django.utils.dateparse import parse_date, parse_time
        d  = parse_date(date)
        st = parse_time(start_time)
        et = parse_time(end_time)
    except Exception:
        return JsonResponse({'clash': False})

    qs = Event.objects.filter(date=d, venue__iexact=venue, status__in=['approved', 'pending'])
    if exclude_id:
        try:
            qs = qs.exclude(pk=int(exclude_id))
        except Exception:
            pass

    for ev in qs:
        if not (et <= ev.start_time or st >= ev.end_time):
            return JsonResponse({
                'clash': True,
                'message': (
                    f'"{ev.title}" is already at {venue} from '
                    f'{ev.start_time.strftime("%I:%M %p")} to '
                    f'{ev.end_time.strftime("%I:%M %p")} on {d.strftime("%b %d")}.'
                )
            })

    return JsonResponse({'clash': False})


# ── F2: ICS Calendar Export ───────────────────────────────────────────────────

def export_ics(request, pk):
    """Generate and download an .ics calendar file for an event."""
    event = get_object_or_404(Event, pk=pk, status='approved')

    from datetime import datetime, timezone as dt_timezone

    # Combine date + time into UTC-aware datetime (server is IST = UTC+5:30)
    def to_ics_dt(d, t):
        naive = datetime.combine(d, t)
        import pytz
        try:
            ist = pytz.timezone('Asia/Kolkata')
            aware = ist.localize(naive)
        except Exception:
            aware = naive.replace(tzinfo=dt_timezone.utc)
        return aware.strftime('%Y%m%dT%H%M%SZ')

    dtstart = to_ics_dt(event.date, event.start_time)
    dtend   = to_ics_dt(event.date, event.end_time)
    now_str = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

    uid = f"event-{event.pk}@campusevents"
    desc = event.description.replace('\n', '\\n').replace(',', '\\,')

    ics_content = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//CampusEvents//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{now_str}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{event.title}\r\n"
        f"DESCRIPTION:{desc}\r\n"
        f"LOCATION:{event.venue}\r\n"
        f"ORGANIZER;CN={event.organizer.get_full_name() or event.organizer.username}:MAILTO:{event.organizer.email}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )

    response = HttpResponse(ics_content, content_type='text/calendar; charset=utf-8')
    safe_title = event.title.replace(' ', '_')[:40]
    response['Content-Disposition'] = f'attachment; filename="{safe_title}.ics"'
    return response


# ── F3: Wishlist / Bookmark ───────────────────────────────────────────────────

@login_required
def toggle_wishlist(request, pk):
    """Toggle wishlist status for an event (AJAX)."""
    if not request.user.is_student:
        return JsonResponse({'success': False, 'error': 'Students only'})

    event = get_object_or_404(Event, pk=pk)
    obj, created = Wishlist.objects.get_or_create(user=request.user, event=event)
    if not created:
        obj.delete()
        return JsonResponse({'success': True, 'wishlisted': False})
    return JsonResponse({'success': True, 'wishlisted': True})


# ── F8: Event Gallery ─────────────────────────────────────────────────────────

def event_gallery(request, pk):
    """View event photo gallery."""
    event = get_object_or_404(Event, pk=pk, status='approved')
    photos = event.photos.all()
    can_upload = (
        request.user.is_authenticated and
        (request.user == event.organizer or request.user.is_admin_user)
    )
    return render(request, 'events/event_gallery.html', {
        'event': event,
        'photos': photos,
        'can_upload': can_upload,
    })


@login_required
def upload_gallery_photo(request, pk):
    """Upload a photo to event gallery (organiser/admin only)."""
    event = get_object_or_404(Event, pk=pk)
    if not (request.user == event.organizer or request.user.is_admin_user):
        messages.error(request, 'Only the organizer or admin can upload photos.')
        return redirect('event_gallery', pk=pk)

    if request.method == 'POST' and request.FILES.get('image'):
        photo = EventPhoto(
            event=event,
            image=request.FILES['image'],
            caption=request.POST.get('caption', ''),
            uploaded_by=request.user,
        )
        photo.save()
        messages.success(request, 'Photo uploaded successfully!')
    return redirect('event_gallery', pk=pk)


@login_required
def delete_gallery_photo(request, photo_id):
    """Delete a gallery photo."""
    photo = get_object_or_404(EventPhoto, pk=photo_id)
    if not (request.user == photo.event.organizer or request.user.is_admin_user):
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    photo.image.delete(save=False)
    photo.delete()
    return JsonResponse({'success': True})


# ── F9: Q&A / Comment Wall ────────────────────────────────────────────────────

@login_required
def ask_question(request, pk):
    """Post a question on the event Q&A wall."""
    event = get_object_or_404(Event, pk=pk)
    if request.method == 'POST':
        q = request.POST.get('question', '').strip()
        if q:
            EventQuestion.objects.create(event=event, asker=request.user, question=q)
            messages.success(request, 'Your question has been posted!')
        else:
            messages.error(request, 'Please enter a question.')
    return redirect('event_detail', pk=pk)


@login_required
def answer_question(request, pk, qid):
    """Organizer/admin answers a Q&A question."""
    event    = get_object_or_404(Event, pk=pk)
    question = get_object_or_404(EventQuestion, pk=qid, event=event)

    if not (request.user == event.organizer or request.user.is_admin_user):
        messages.error(request, 'Only the organizer or admin can answer questions.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        ans = request.POST.get('answer', '').strip()
        if ans:
            question.answer = ans
            question.answered_by = request.user
            question.answered_at = timezone.now()
            question.save()
            # Notify the asker
            create_notification(
                question.asker,
                f'Your question was answered — {event.title}',
                f'The organizer answered your question on "{event.title}".',
                'general',
                link=f'/events/{event.pk}/'
            )
            messages.success(request, 'Answer posted!')
        else:
            messages.error(request, 'Please enter an answer.')
    return redirect('event_detail', pk=pk)


# ── F11: Team Registration ────────────────────────────────────────────────────

@login_required
def create_team(request, pk):
    """Team leader creates a team and auto-registers."""
    event = get_object_or_404(Event, pk=pk, status='approved', team_event=True)

    if not request.user.is_student:
        messages.error(request, 'Only students can join teams.')
        return redirect('event_detail', pk=pk)

    if Registration.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=pk)

    if event.is_full:
        messages.error(request, 'Event is full.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        team_name = request.POST.get('team_name', '').strip()
        if not team_name:
            messages.error(request, 'Please enter a team name.')
            return redirect('event_detail', pk=pk)

        import secrets
        code = secrets.token_hex(4).upper()  # 8-char hex code
        team = Team.objects.create(event=event, leader=request.user, name=team_name, code=code)

        registration = Registration(event=event, student=request.user, team=team)
        registration.generate_qr_code()
        registration.save()
        send_registration_email(registration)

        messages.success(request,
            f'Team "{team_name}" created! Share code: {code} with your teammates.')
        return redirect('event_detail', pk=pk)

    return redirect('event_detail', pk=pk)


@login_required
def join_team(request, pk):
    """Student joins an existing team using the team code."""
    event = get_object_or_404(Event, pk=pk, status='approved', team_event=True)

    if not request.user.is_student:
        messages.error(request, 'Only students can join teams.')
        return redirect('event_detail', pk=pk)

    if Registration.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=pk)

    if request.method == 'POST':
        code = request.POST.get('team_code', '').strip().upper()
        try:
            team = Team.objects.get(event=event, code=code)
        except Team.DoesNotExist:
            messages.error(request, f'No team found with code "{code}".')
            return redirect('event_detail', pk=pk)

        if team.is_full:
            messages.error(request, f'Team "{team.name}" is full (max {event.max_team_size} members).')
            return redirect('event_detail', pk=pk)

        if event.is_full:
            messages.error(request, 'Event is full.')
            return redirect('event_detail', pk=pk)

        registration = Registration(event=event, student=request.user, team=team)
        registration.generate_qr_code()
        registration.save()
        send_registration_email(registration)

        messages.success(request, f'You joined team "{team.name}"!')
        return redirect('event_detail', pk=pk)

    return redirect('event_detail', pk=pk)