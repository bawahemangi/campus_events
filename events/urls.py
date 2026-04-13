from django.urls import path
from . import views
from . import payment_views

urlpatterns = [
    # Event listing and detail
    path('', views.event_list, name='event_list'),
    path('<int:pk>/', views.event_detail, name='event_detail'),

    # Free event registration
    path('<int:pk>/register/', views.register_for_event, name='register_for_event'),
    path('cancel/<int:pk>/', views.cancel_registration, name='cancel_registration'),

    # ── PAYMENT ROUTES ────────────────────────────────────────────────
    path('<int:event_pk>/pay/', payment_views.initiate_payment, name='initiate_payment'),
    path('payment/verify/', payment_views.verify_payment, name='verify_payment'),
    path('<int:event_pk>/payment-failed/', payment_views.payment_failed, name='payment_failed'),
    path('payment/history/', payment_views.payment_history, name='payment_history'),

    # Feedback
    path('<int:pk>/feedback/', views.submit_feedback, name='submit_feedback'),

    # Organizer event management
    path('create/', views.create_event, name='create_event'),
    path('<int:pk>/edit/', views.edit_event, name='edit_event'),
    path('<int:pk>/scan/', views.scan_qr, name='scan_qr'),

    # Attendance
    path('attendance/mark/', views.mark_attendance_api, name='mark_attendance_api'),
    path('attendance/unmark/<int:registration_id>/', views.unmark_attendance, name='unmark_attendance'),
    path('check-clash/', views.clash_check_api, name='clash_check_api'),
    path('attendance/manual/<int:registration_id>/', views.mark_attendance_manual, name='mark_attendance_manual'),

    # Certificate
    path('certificate/<int:registration_id>/', views.download_certificate, name='download_certificate'),

    # APIs
    path('<int:pk>/seats/', views.seats_left_api, name='seats_left_api'),
    path('notifications/', views.notifications_api, name='notifications_api'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/all/', views.all_notifications, name='all_notifications'),
]
