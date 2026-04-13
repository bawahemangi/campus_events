from django.urls import path
from events.dashboard_views import (
    dashboard, student_dashboard, organizer_dashboard,
    admin_dashboard, approve_event, reject_event,
    admin_event_detail, analytics, admin_attendance
)

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('student/', student_dashboard, name='student_dashboard'),
    path('organizer/', organizer_dashboard, name='organizer_dashboard'),
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('admin/event/<int:pk>/', admin_event_detail, name='admin_event_detail'),
    path('admin/approve/<int:pk>/', approve_event, name='approve_event'),
    path('admin/reject/<int:pk>/', reject_event, name='reject_event'),
    path('admin/analytics/', analytics, name='analytics'),
    path('admin/attendance/<int:pk>/', admin_attendance, name='admin_attendance'),
]
