from django.contrib import admin
from .models import Event, Registration, Feedback, Notification

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'date', 'category', 'status', 'registered_count']
    list_filter = ['status', 'category', 'date']
    search_fields = ['title', 'venue']

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['student', 'event', 'registered_at', 'attended']
    list_filter = ['attended']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['student', 'event', 'rating', 'created_at']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']

from .models import SliderItem

@admin.register(SliderItem)
class SliderItemAdmin(admin.ModelAdmin):
    list_display  = ['title', 'slide_type', 'is_active', 'order', 'created_at']
    list_filter   = ['slide_type', 'is_active']
    list_editable = ['is_active', 'order']
    search_fields = ['title', 'subtitle']
