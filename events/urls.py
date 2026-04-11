from django.urls import path
from . import views

urlpatterns = [
    # Event listing and detail
    path('', views.event_list, name='event_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    
    # Registration
    path('<int:pk>/register/', views.register_for_event, name='register_for_event'),
    path('cancel/<int:pk>/', views.cancel_registration, name='cancel_registration'),
    
    # Feedback
    path('<int:pk>/feedback/', views.submit_feedback, name='submit_feedback'),
    
    # Organizer event management
    path('create/', views.create_event, name='create_event'),
    path('<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('<int:pk>/scan/', views.scan_qr, name='scan_qr'),
    
    # Attendance
    path('attendance/mark/', views.mark_attendance_api, name='mark_attendance_api'),
    path('attendance/manual/<int:registration_id>/', views.mark_attendance_manual, name='mark_attendance_manual'),
    
    # Certificate
    path('certificate/<int:registration_id>/', views.download_certificate, name='download_certificate'),
    
    # APIs
    path('<int:pk>/seats/', views.seats_left_api, name='seats_left_api'),
    path('notifications/', views.notifications_api, name='notifications_api'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
]
