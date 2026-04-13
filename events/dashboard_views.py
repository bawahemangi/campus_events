"""
Dashboard views for Student, Organizer, and Admin
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.http import JsonResponse
from events.models import Event, Registration, Feedback, Notification, Payment
from events.utils import get_event_recommendations, create_notification, send_event_approved_email, send_event_rejected_email
from users.models import CustomUser


@login_required
def dashboard(request):
    """Route to role-appropriate dashboard."""
    if request.user.is_admin_user:
        return redirect('admin_dashboard')
    elif request.user.is_organizer:
        return redirect('organizer_dashboard')
    else:
        return redirect('student_dashboard')


@login_required
def student_dashboard(request):
    """Student dashboard."""
    if not request.user.is_student:
        return redirect('dashboard')
    
    today = timezone.now().date()
    registrations = Registration.objects.filter(
        student=request.user
    ).select_related('event').order_by('-registered_at')
    
    upcoming_registrations = [r for r in registrations if not r.event.is_past]
    past_registrations = [r for r in registrations if r.event.is_past]
    attended_count = sum(1 for r in registrations if r.attended)
    
    # Recommendations
    recommendations = get_event_recommendations(request.user, limit=4)
    
    # Unread notifications
    notifications = request.user.notifications.filter(is_read=False)[:5]
    
    # Get rank in leaderboard
    better_students = CustomUser.objects.filter(
        role='student',
        participation_points__gt=request.user.participation_points
    ).count()
    rank = better_students + 1
    
    context = {
        'upcoming_registrations': upcoming_registrations,
        'past_registrations': past_registrations,
        'attended_count': attended_count,
        'total_registered': registrations.count(),
        'recommendations': recommendations,
        'notifications': notifications,
        'points': request.user.participation_points,
        'rank': rank,
    }
    return render(request, 'dashboard/student.html', context)


@login_required
def organizer_dashboard(request):
    """Organizer dashboard."""
    if not request.user.is_organizer:
        return redirect('dashboard')
    
    events = Event.objects.filter(organizer=request.user).order_by('-created_at')
    
    # Stats per event
    events_with_stats = []
    for event in events:
        events_with_stats.append({
            'event': event,
            'registered': event.registered_count,
            'attended': event.attendance_count,
            'seats_left': event.seats_left,
            'avg_rating': event.average_rating,
        })
    
    total_participants = sum(e['registered'] for e in events_with_stats)
    total_attended = sum(e['attended'] for e in events_with_stats)
    approved_events = events.filter(status='approved').count()
    pending_events = events.filter(status='pending').count()
    
    # Category breakdown for the organizer's events
    category_counts = events.values('category').annotate(count=Count('id'))
    
    notifications = request.user.notifications.filter(is_read=False)[:5]
    
    context = {
        'events_with_stats': events_with_stats,
        'total_participants': total_participants,
        'total_attended': total_attended,
        'approved_events': approved_events,
        'pending_events': pending_events,
        'category_counts': list(category_counts),
        'notifications': notifications,
        'total_events': events.count(),
    }
    return render(request, 'dashboard/organizer.html', context)


@login_required
def admin_dashboard(request):
    """Admin dashboard with full analytics."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    today = timezone.now().date()
    
    # Event stats
    all_events = Event.objects.all()
    pending_events = all_events.filter(status='pending').order_by('-created_at')
    approved_events = all_events.filter(status='approved')
    
    # User stats
    total_students = CustomUser.objects.filter(role='student').count()
    total_organizers = CustomUser.objects.filter(role='organizer').count()
    total_registrations = Registration.objects.count()
    total_attended = Registration.objects.filter(attended=True).count()

    # Payment stats
    from django.db.models import Sum
    total_revenue = Payment.objects.filter(status='completed').aggregate(
        total=Sum('amount'))['total'] or 0
    paid_events_count = Event.objects.filter(is_paid=True, status='approved').count()
    
    # Most popular category
    category_stats = (
        Registration.objects.values('event__category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Most popular events (by registrations)
    popular_events = all_events.filter(status='approved').annotate(
        reg_count=Count('registrations')
    ).order_by('-reg_count')[:5]
    
    # Recent registrations
    recent_registrations = Registration.objects.select_related(
        'student', 'event'
    ).order_by('-registered_at')[:10]
    
    # Upcoming events
    upcoming_events = approved_events.filter(date__gte=today).order_by('date')[:5]
    
    notifications = request.user.notifications.filter(is_read=False)[:5]
    
    context = {
        'pending_events': pending_events,
        'total_events': all_events.count(),
        'approved_count': approved_events.count(),
        'pending_count': pending_events.count(),
        'total_students': total_students,
        'total_organizers': total_organizers,
        'total_registrations': total_registrations,
        'total_attended': total_attended,
        'category_stats': list(category_stats),
        'popular_events': popular_events,
        'recent_registrations': recent_registrations,
        'upcoming_events': upcoming_events,
        'notifications': notifications,
        'total_revenue': total_revenue,
        'paid_events_count': paid_events_count,
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
def approve_event(request, pk):
    """Admin approves an event."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    event = get_object_or_404(Event, pk=pk)
    event.status = 'approved'
    event.rejection_reason = ''
    event.save()

    # Notify organizer (in-app + email)
    create_notification(
        event.organizer,
        f'Event Approved: {event.title}',
        f'Your event "{event.title}" has been approved and is now live!',
        'approval',
        link=f'/events/{event.pk}/'
    )
    send_event_approved_email(event)

    messages.success(request, f'"{event.title}" has been approved.')
    return redirect('admin_dashboard')


@login_required
def reject_event(request, pk):
    """Admin rejects an event."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    event = get_object_or_404(Event, pk=pk)
    reason = request.POST.get('reason', 'No reason provided.')
    event.status = 'rejected'
    event.rejection_reason = reason
    event.save()

    create_notification(
        event.organizer,
        f'Event Rejected: {event.title}',
        f'Your event "{event.title}" was rejected. Reason: {reason}',
        'rejection',
        link=f'/dashboard/organizer/'
    )
    send_event_rejected_email(event)

    messages.warning(request, f'"{event.title}" has been rejected.')
    return redirect('admin_dashboard')


@login_required
def admin_event_detail(request, pk):
    """Admin view of event details."""
    if not request.user.is_admin_user:
        return redirect('dashboard')
    
    event = get_object_or_404(Event, pk=pk)
    registrations = event.registrations.select_related('student').order_by('-registered_at')
    
    context = {
        'event': event,
        'registrations': registrations,
    }
    return render(request, 'dashboard/admin_event_detail.html', context)


@login_required
def analytics(request):
    """Analytics page for admin."""
    if not request.user.is_admin_user:
        return redirect('dashboard')
    
    # Registrations per category
    category_data = (
        Registration.objects.values('event__category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    # Registrations per event
    event_data = (
        Event.objects.filter(status='approved')
        .annotate(reg_count=Count('registrations'))
        .order_by('-reg_count')[:10]
    )
    
    # Monthly registration trend (last 6 months)
    from django.db.models.functions import TruncMonth
    monthly_data = (
        Registration.objects.annotate(month=TruncMonth('registered_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    
    context = {
        'category_data': list(category_data),
        'event_data': list(event_data),
        'monthly_data': list(monthly_data),
    }
    return render(request, 'dashboard/analytics.html', context)


@login_required
def admin_attendance(request, pk):
    """Admin can view and manage attendance for any event."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    event = get_object_or_404(Event, pk=pk)
    registrations = event.registrations.select_related('student', 'payment').order_by(
        'student__last_name', 'student__first_name'
    )

    context = {
        'event':          event,
        'registrations':  registrations,
        'attended_count': event.attendance_count,
        'total_count':    event.registered_count,
        'is_admin_view':  True,
    }
    return render(request, 'events/scan_qr.html', context)
