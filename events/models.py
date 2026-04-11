"""
Events app models - Event, Registration, Feedback, Certificate, Payment
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import qrcode
import os
from io import BytesIO
from django.core.files.base import ContentFile


class Event(models.Model):
    """Main event model."""

    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('cultural', 'Cultural'),
        ('sports', 'Sports'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    # Basic info
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')

    # Organizer
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events'
    )

    # Date & Venue
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    venue = models.CharField(max_length=200)

    # Capacity
    max_capacity = models.IntegerField(default=100)

    # Media
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Certificate template
    certificate_template = models.TextField(
        default='This is to certify that {student_name} has successfully participated in {event_name} held on {event_date}.'
    )

    # ── PAYMENT FIELDS ──────────────────────────────────────────────────
    is_paid = models.BooleanField(default=False, help_text='Is this a paid event?')
    registration_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.00,
        help_text='Fee in INR (0 = free)'
    )

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def seats_left(self):
        return self.max_capacity - self.registered_count

    @property
    def is_full(self):
        return self.seats_left <= 0

    @property
    def is_upcoming(self):
        return self.date >= timezone.now().date()

    @property
    def is_past(self):
        return self.date < timezone.now().date()

    @property
    def average_rating(self):
        feedbacks = self.feedbacks.all()
        if not feedbacks:
            return 0
        return round(sum(f.rating for f in feedbacks) / len(feedbacks), 1)

    @property
    def attendance_count(self):
        return self.registrations.filter(attended=True).count()

    class Meta:
        ordering = ['date', 'start_time']


class Payment(models.Model):
    """Razorpay payment record for a registration."""

    STATUS_CHOICES = [
        ('created',   'Order Created'),
        ('pending',   'Payment Pending'),
        ('completed', 'Payment Completed'),
        ('failed',    'Payment Failed'),
        ('refunded',  'Refunded'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='payments')

    # Razorpay IDs
    razorpay_order_id   = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True)

    amount       = models.DecimalField(max_digits=8, decimal_places=2)   # in INR
    amount_paise = models.IntegerField(default=0)                         # for Razorpay API
    currency     = models.CharField(max_length=5, default='INR')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment ₹{self.amount} by {self.student.username} for {self.event.title} [{self.status}]"

    @property
    def is_successful(self):
        return self.status == 'completed'


class Registration(models.Model):
    """Student registration for an event."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    # Payment link (null for free events)
    payment = models.OneToOneField(
        Payment, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='registration'
    )

    # QR code for attendance
    qr_code   = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    qr_token  = models.CharField(max_length=100, unique=True, blank=True)

    # Certificate
    certificate      = models.FileField(upload_to='certificates/', blank=True, null=True)
    certificate_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'student')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.student.username} → {self.event.title}"

    def generate_qr_code(self):
        """Generate a unique QR code for this registration."""
        import uuid
        if not self.qr_token:
            self.qr_token = str(uuid.uuid4())

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr_data = f"CAMPUS_EVENT|{self.qr_token}|{self.event.id}|{self.student.id}"
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"qr_{self.qr_token[:8]}.png"
        self.qr_code.save(filename, ContentFile(buffer.read()), save=False)
        return self.qr_code

    def mark_attended(self):
        """Mark this registration as attended and award points."""
        if not self.attended:
            self.attended = True
            self.save()
            self.student.participation_points += 10
            self.student.save()


class Feedback(models.Model):
    """Student feedback for an event."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    rating  = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'student')

    def __str__(self):
        return f"{self.student.username} rated {self.event.title}: {self.rating}/5"


class Notification(models.Model):
    """In-app notifications for users."""

    TYPE_CHOICES = [
        ('registration', 'Registration Confirmed'),
        ('payment',      'Payment Received'),
        ('reminder',     'Event Reminder'),
        ('approval',     'Event Approved'),
        ('rejection',    'Event Rejected'),
        ('certificate',  'Certificate Available'),
        ('general',      'General'),
    ]

    user              = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title             = models.CharField(max_length=200)
    message           = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='general')
    is_read           = models.BooleanField(default=False)
    link              = models.CharField(max_length=300, blank=True)   # optional click-through URL
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
