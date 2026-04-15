"""
Public homepage — shows the hero slider + upcoming events preview.
Accessible to everyone (logged in or not).
"""
from django.shortcuts import render
from django.utils import timezone
from .models import SliderItem, Event


def homepage(request):
    # Active slider items
    slides = SliderItem.objects.filter(is_active=True,image__isnull=False).exclude(image='').order_by('order', '-created_at')
    today = timezone.now().date()

    # Next 6 upcoming approved events for the "What's Coming" strip
    upcoming = Event.objects.filter(
        status='approved', date__gte=today
    ).order_by('date')[:6]

    # 3 recently concluded events for the "From Our Archives" strip
    recent_past = Event.objects.filter(
        status='approved', date__lt=today
    ).order_by('-date')[:3]

    context = {
        'slides':      slides,
        'upcoming':    upcoming,
        'recent_past': recent_past,
        'today':       today,
    }
    return render(request, 'home.html', context)
