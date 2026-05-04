"""
Events app models - Event, Registration, Feedback, Certificate, Payment
+ New: Wishlist (F3), EventPhoto (F8), EventQuestion (F9), Team (F11)
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

    # ── F11: TEAM EVENT FIELDS ───────────────────────────────────────────
    team_event = models.BooleanField(default=False, help_text='Require team registration?')
    min_team_size = models.PositiveIntegerField(default=2)
    max_team_size = models.PositiveIntegerField(default=5)

    # ── F10: BULK EMAIL THROTTLE ─────────────────────────────────────────
    last_bulk_email_at = models.DateTimeField(null=True, blank=True)

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

    razorpay_order_id   = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    razorpay_signature  = models.CharField(max_length=200, blank=True)

    amount       = models.DecimalField(max_digits=8, decimal_places=2)
    amount_paise = models.IntegerField(default=0)
    currency     = models.CharField(max_length=5, default='INR')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment Rs.{self.amount} by {self.student.username} for {self.event.title} [{self.status}]"

    @property
    def is_successful(self):
        return self.status == 'completed'


# ── F11: Team Model ───────────────────────────────────────────────────────────

class Team(models.Model):
    """A team for team-based event registration."""
    event  = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='teams')
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='led_teams'
    )
    name       = models.CharField(max_length=100)
    code       = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Team '{self.name}' for {self.event.title}"

    @property
    def member_count(self):
        return self.registrations.count()

    @property
    def is_full(self):
        return self.member_count >= self.event.max_team_size


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

    payment = models.OneToOneField(
        Payment, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='registration'
    )

    qr_code  = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    qr_token = models.CharField(max_length=100, unique=True, blank=True)

    certificate      = models.FileField(upload_to='certificates/', blank=True, null=True)
    certificate_sent = models.BooleanField(default=False)

    # F11: Team link
    team = models.ForeignKey(
        Team, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='registrations'
    )

    class Meta:
        unique_together = ('event', 'student')
        ordering = ['-registered_at']

    def __str__(self):
        return f"{self.student.username} -> {self.event.title}"

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
    link              = models.CharField(max_length=300, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"


class SliderItem(models.Model):
    """Homepage slider item."""
    TYPE_CHOICES = [
        ('upcoming',  'Upcoming Event'),
        ('past',      'Past Event Highlight'),
        ('annual',    'Annual/Big Event'),
        ('gallery',   'Photo Gallery'),
        ('custom',    'Custom Banner'),
    ]

    title       = models.CharField(max_length=200)
    subtitle    = models.CharField(max_length=300, blank=True)
    image       = models.ImageField(upload_to='slider/')
    slide_type  = models.CharField(max_length=20, choices=TYPE_CHOICES, default='upcoming')
    linked_event = models.ForeignKey(
        Event, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='slider_items',
    )
    cta_text    = models.CharField(max_length=60, blank=True, default='Learn More')
    cta_url     = models.CharField(max_length=300, blank=True)
    TEXT_COLOR_CHOICES = [('light', 'White text'), ('dark', 'Dark text')]
    text_color  = models.CharField(max_length=10, choices=TEXT_COLOR_CHOICES, default='light')
    is_active   = models.BooleanField(default=True)
    order       = models.PositiveIntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='slider_items_created'
    )

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"[{self.get_slide_type_display()}] {self.title}"

    @property
    def final_cta_url(self):
        if self.cta_url:
            return self.cta_url
        if self.linked_event:
            return f'/events/{self.linked_event.pk}/'
        return '/events/'


# ── F3: Wishlist ──────────────────────────────────────────────────────────────

class Wishlist(models.Model):
    """Students can bookmark/wishlist events."""
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} wishlist -> {self.event.title}"


# ── F8: Event Gallery ─────────────────────────────────────────────────────────

class EventPhoto(models.Model):
    """Photos uploaded to an event gallery."""
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='photos')
    image       = models.ImageField(upload_to='gallery/')
    caption     = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo for {self.event.title}"


# ── F9: Event Q&A ─────────────────────────────────────────────────────────────

class EventQuestion(models.Model):
    """Q&A wall for events."""
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='questions')
    asker       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_questions')
    question    = models.TextField()
    answer      = models.TextField(blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='event_answers'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q on {self.event.title} by {self.asker.username}"
