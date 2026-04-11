"""
Events app views - Event listing, detail, registration, QR, feedback
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.utils import timezone
from django.db.models import Count, Avg, Q
from .models import Event, Registration, Feedback, Notification
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
    
    today = timezone.now().date()
    upcoming_events = events.filter(date__gte=today).order_by('date')
    past_events = events.filter(date__lt=today).order_by('-date')
    
    # Get user's registered event IDs
    registered_ids = []
    if request.user.is_authenticated:
        registered_ids = list(
            Registration.objects.filter(student=request.user)
            .values_list('event_id', flat=True)
        )
    
    context = {
        'form': form,
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'registered_ids': registered_ids,
    }
    return render(request, 'events/event_list.html', context)


def event_detail(request, pk):
    """Event detail page."""
    event = get_object_or_404(Event, pk=pk)
    
    # Non-approved events only visible to organizer/admin
    if event.status != 'approved':
        if not request.user.is_authenticated:
            raise Http404
        if not (request.user == event.organizer or request.user.is_admin_user):
            raise Http404
    
    user_registration = None
    user_feedback = None
    feedback_form = None
    
    if request.user.is_authenticated:
        user_registration = Registration.objects.filter(
            event=event, student=request.user
        ).first()
        
        user_feedback = Feedback.objects.filter(
            event=event, student=request.user
        ).first()
        
        # Show feedback form if attended and no feedback yet
        if user_registration and user_registration.attended and not user_feedback:
            feedback_form = FeedbackForm()
    
    feedbacks = event.feedbacks.select_related('student').order_by('-created_at')
    
    context = {
        'event': event,
        'user_registration': user_registration,
        'user_feedback': user_feedback,
        'feedback_form': feedback_form,
        'feedbacks': feedbacks,
        'seats_left': event.seats_left,
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
    
    # Check if already registered
    if Registration.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=pk)
    
    # Create registration
    registration = Registration(event=event, student=request.user)
    registration.generate_qr_code()
    registration.save()
    
    # Send confirmation email
    send_registration_email(registration)
    
    # Create notification
    create_notification(
        request.user,
        f'Registered: {event.title}',
        f'You have successfully registered for {event.title} on {event.date}.',
        'registration'
    )
    
    messages.success(request, f'🎉 Successfully registered for {event.title}! Check your email for QR code.')
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
    
    # Check if attended
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
            messages.success(request, 'Thank you for your feedback! ⭐')
    
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
            
            messages.success(request, '✅ Event submitted for admin approval!')
            return redirect('organizer_dashboard')
    else:
        form = EventForm()
    
    return render(request, 'events/create_event.html', {'form': form})


@login_required
def edit_event(request, pk):
    """Organizer edits an event."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    
    if event.status == 'approved' and event.registered_count > 0:
        messages.warning(request, 'Event has registrations; some fields are locked.')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            event.status = 'pending'  # Re-submit for approval
            event.save()
            messages.success(request, 'Event updated and resubmitted for approval.')
            return redirect('organizer_dashboard')
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/create_event.html', {'form': form, 'event': event})


@login_required
def scan_qr(request, pk):
    """Organizer QR scan page for attendance."""
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    registrations = event.registrations.select_related('student').order_by('-registered_at')
    
    context = {
        'event': event,
        'registrations': registrations,
        'attended_count': event.attendance_count,
        'total_count': event.registered_count,
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
        
        # Check organizer owns this event
        if registration.event.organizer != request.user:
            return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
        if registration.attended:
            return JsonResponse({
                'success': False,
                'already_marked': True,
                'message': f'{registration.student.get_full_name() or registration.student.username} already marked present.'
            })
        
        registration.mark_attended()
        
        # Generate certificate
        generate_certificate(registration)
        send_certificate_email(registration)
        
        # Notify student
        create_notification(
            registration.student,
            f'Attendance Marked: {registration.event.title}',
            f'Your attendance for {registration.event.title} has been marked. Check your email for your certificate!',
            'certificate'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'✅ Attendance marked for {registration.student.get_full_name() or registration.student.username}!',
            'student_name': registration.student.get_full_name() or registration.student.username,
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
