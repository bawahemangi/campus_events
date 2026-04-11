"""
Utility functions:
  - Rich HTML Gmail notifications (registration, payment, reminder, certificate)
  - PDF certificate generation (ReportLab)
  - In-app notifications
  - Event recommendations
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from django.core.files.base import ContentFile
import os
from io import BytesIO


# ─────────────────────────────────────────────────────────────────────
#  SHARED EMAIL HELPERS
# ─────────────────────────────────────────────────────────────────────

def _html_wrap(title, body_html, accent='#6c47ff'):
    """Wrap HTML body in a polished email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ margin:0; padding:0; background:#f0f2f8; font-family:'Segoe UI',Arial,sans-serif; }}
  .wrap {{ max-width:600px; margin:30px auto; background:#fff; border-radius:16px; overflow:hidden; box-shadow:0 4px 24px rgba(0,0,0,.10); }}
  .header {{ background:linear-gradient(135deg,{accent},#1a237e); padding:36px 40px 30px; text-align:center; }}
  .header h1 {{ margin:0; color:#fff; font-size:26px; font-weight:800; letter-spacing:-0.5px; }}
  .header p  {{ margin:6px 0 0; color:rgba(255,255,255,.75); font-size:14px; }}
  .body  {{ padding:36px 40px; color:#1a1a2e; line-height:1.7; }}
  .body h2 {{ margin:0 0 16px; font-size:20px; color:#1a1a2e; }}
  .body p  {{ margin:0 0 14px; font-size:15px; color:#374151; }}
  .info-box {{ background:#f8f9ff; border-left:4px solid {accent}; border-radius:0 10px 10px 0; padding:16px 20px; margin:20px 0; }}
  .info-box div {{ margin-bottom:6px; font-size:14px; color:#374151; }}
  .info-box div:last-child {{ margin-bottom:0; }}
  .info-label {{ font-weight:700; color:#1a1a2e; min-width:80px; display:inline-block; }}
  .btn {{ display:inline-block; background:{accent}; color:#fff!important; text-decoration:none; padding:13px 32px; border-radius:10px; font-weight:700; font-size:15px; margin:20px 0; }}
  .badge {{ display:inline-block; background:{accent}22; color:{accent}; border:1px solid {accent}44; padding:4px 14px; border-radius:20px; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; }}
  .footer {{ background:#f8f9ff; padding:20px 40px; text-align:center; font-size:12px; color:#9ca3af; border-top:1px solid #e5e7eb; }}
  .footer a {{ color:{accent}; text-decoration:none; }}
  .divider {{ border:none; border-top:1px solid #e5e7eb; margin:24px 0; }}
  .success-icon {{ font-size:48px; text-align:center; margin-bottom:16px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>🎓 CampusEvents</h1>
    <p>{title}</p>
  </div>
  <div class="body">
    {body_html}
  </div>
  <div class="footer">
    <p>© {timezone.now().year} CampusEvents Platform &nbsp;|&nbsp; <a href="{settings.SITE_URL}">Visit Website</a></p>
    <p>This is an automated email — please do not reply.</p>
  </div>
</div>
</body>
</html>"""


def _send_html_email(subject, to_email, html_content, attachments=None):
    """Send an HTML email with optional file attachments."""
    try:
        if not to_email:
            return False
        # Plain-text fallback (strip tags roughly)
        import re
        plain = re.sub(r'<[^>]+>', ' ', html_content)
        plain = re.sub(r'\s+', ' ', plain).strip()

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_content, "text/html")

        if attachments:
            for filepath in attachments:
                if filepath and os.path.exists(filepath):
                    msg.attach_file(filepath)

        msg.send(fail_silently=True)
        return True
    except Exception as e:
        print(f"[Email Error] {e}")
        return False


# ─────────────────────────────────────────────────────────────────────
#  1. REGISTRATION CONFIRMATION EMAIL
# ─────────────────────────────────────────────────────────────────────

def send_registration_email(registration):
    """Rich HTML confirmation email with QR code attached."""
    event   = registration.event
    student = registration.student
    name    = student.get_full_name() or student.username
    site    = settings.SITE_URL

    free_paid = f'<span style="color:#06d6a0;font-weight:700;">FREE</span>' if not event.is_paid else \
                f'<span style="color:#6c47ff;font-weight:700;">₹{event.registration_fee}</span>'

    body = f"""
    <div class="success-icon">🎉</div>
    <h2>You're registered, {name.split()[0]}!</h2>
    <p>Your registration for <strong>{event.title}</strong> is confirmed. See you there!</p>

    <div class="info-box">
      <div><span class="info-label">📅 Date</span> {event.date.strftime('%A, %B %d, %Y')}</div>
      <div><span class="info-label">⏰ Time</span> {event.start_time.strftime('%I:%M %p')} – {event.end_time.strftime('%I:%M %p')}</div>
      <div><span class="info-label">📍 Venue</span> {event.venue}</div>
      <div><span class="info-label">🏷 Category</span> <span class="badge">{event.get_category_display()}</span></div>
      <div><span class="info-label">💰 Fee</span> {free_paid}</div>
      <div><span class="info-label">👤 Organizer</span> {event.organizer.get_full_name() or event.organizer.username}</div>
    </div>

    <p>📱 <strong>Your unique QR code is attached</strong> to this email. Show it at the entrance on event day to mark your attendance.</p>
    <p>You can also view your registration and download your QR code anytime from your dashboard.</p>

    <a href="{site}/events/{event.pk}/" class="btn">View Event Details →</a>

    <hr class="divider">
    <p style="font-size:13px;color:#9ca3af;">
      If you need to cancel your registration, please do so before the event date via your dashboard.
    </p>
    """

    subject = f"✅ Registered: {event.title} — {event.date.strftime('%b %d')}"
    html    = _html_wrap(f"Registration Confirmed for {event.title}", body)

    attachments = []
    if registration.qr_code:
        try:
            attachments.append(registration.qr_code.path)
        except Exception:
            pass

    _send_html_email(subject, student.email, html, attachments)


# ─────────────────────────────────────────────────────────────────────
#  2. PAYMENT CONFIRMATION EMAIL
# ─────────────────────────────────────────────────────────────────────

def send_payment_confirmation_email(payment):
    """Send payment success email with receipt details."""
    event   = payment.event
    student = payment.student
    name    = student.get_full_name() or student.username
    site    = settings.SITE_URL
    reg     = getattr(payment, 'registration', None)

    body = f"""
    <div class="success-icon">💳</div>
    <h2>Payment Successful!</h2>
    <p>Hi {name.split()[0]}, your payment for <strong>{event.title}</strong> has been received and your registration is confirmed.</p>

    <div class="info-box">
      <div><span class="info-label">🎫 Event</span> {event.title}</div>
      <div><span class="info-label">📅 Date</span> {event.date.strftime('%A, %B %d, %Y')}</div>
      <div><span class="info-label">⏰ Time</span> {event.start_time.strftime('%I:%M %p')} – {event.end_time.strftime('%I:%M %p')}</div>
      <div><span class="info-label">📍 Venue</span> {event.venue}</div>
      <div><span class="info-label">💰 Amount Paid</span> <strong style="color:#06d6a0;">₹{payment.amount}</strong></div>
      <div><span class="info-label">🔖 Payment ID</span> <code style="font-size:12px;">{payment.razorpay_payment_id or 'N/A'}</code></div>
      <div><span class="info-label">📋 Order ID</span> <code style="font-size:12px;">{payment.razorpay_order_id or 'N/A'}</code></div>
    </div>

    <p>Keep your Payment ID for your records. You can also view your payment receipt from your dashboard.</p>
    {"<p>📱 <strong>Your attendance QR code is attached</strong> to this email.</p>" if reg and reg.qr_code else ""}

    <a href="{site}/dashboard/student/" class="btn">Go to My Dashboard →</a>
    """

    subject = f"💳 Payment Confirmed ₹{payment.amount} — {event.title}"
    html    = _html_wrap("Payment Confirmed", body, accent='#06d6a0')

    attachments = []
    if reg and reg.qr_code:
        try:
            attachments.append(reg.qr_code.path)
        except Exception:
            pass

    _send_html_email(subject, student.email, html, attachments)


# ─────────────────────────────────────────────────────────────────────
#  3. EVENT REMINDER EMAIL  (send 1 day before)
# ─────────────────────────────────────────────────────────────────────

def send_event_reminder(registration):
    """Reminder email sent the day before the event."""
    event   = registration.event
    student = registration.student
    name    = student.get_full_name() or student.username
    site    = settings.SITE_URL

    body = f"""
    <div class="success-icon">⏰</div>
    <h2>Reminder: Your event is tomorrow!</h2>
    <p>Hi {name.split()[0]}, just a friendly reminder that <strong>{event.title}</strong> is happening tomorrow. Don't miss it!</p>

    <div class="info-box">
      <div><span class="info-label">📅 Date</span> <strong>{event.date.strftime('%A, %B %d, %Y')}</strong></div>
      <div><span class="info-label">⏰ Time</span> {event.start_time.strftime('%I:%M %p')} – {event.end_time.strftime('%I:%M %p')}</div>
      <div><span class="info-label">📍 Venue</span> {event.venue}</div>
      <div><span class="info-label">🏷 Category</span> <span class="badge">{event.get_category_display()}</span></div>
    </div>

    <p>✅ <strong>What to bring:</strong></p>
    <ul style="color:#374151;font-size:15px;line-height:2;">
      <li>Your QR code (attached to your registration confirmation email)</li>
      <li>Your college ID card</li>
      {"<li>Your payment receipt</li>" if event.is_paid else ""}
    </ul>

    <a href="{site}/events/{event.pk}/" class="btn">View Event Details →</a>

    <hr class="divider">
    <p style="font-size:13px;color:#9ca3af;">
      You're receiving this because you registered for this event. 
      <a href="{site}/dashboard/student/" style="color:#6c47ff;">Manage your registrations</a>
    </p>
    """

    subject = f"⏰ Tomorrow: {event.title} — Don't Forget!"
    html    = _html_wrap(f"Event Reminder: {event.title}", body, accent='#ff6b6b')
    _send_html_email(subject, student.email, html)


# ─────────────────────────────────────────────────────────────────────
#  4. CERTIFICATE EMAIL
# ─────────────────────────────────────────────────────────────────────

def send_certificate_email(registration):
    """Send attendance certificate via email."""
    event   = registration.event
    student = registration.student
    name    = student.get_full_name() or student.username
    site    = settings.SITE_URL

    body = f"""
    <div class="success-icon">🏆</div>
    <h2>Congratulations, {name.split()[0]}!</h2>
    <p>You successfully attended <strong>{event.title}</strong>. 
       Your Certificate of Participation is attached to this email.</p>

    <div class="info-box">
      <div><span class="info-label">🎫 Event</span> {event.title}</div>
      <div><span class="info-label">📅 Date</span> {event.date.strftime('%B %d, %Y')}</div>
      <div><span class="info-label">🏷 Category</span> <span class="badge">{event.get_category_display()}</span></div>
      <div><span class="info-label">⭐ Points</span> +10 participation points added to your profile</div>
    </div>

    <p>📄 Your certificate PDF is attached. You can also download it anytime from your dashboard.</p>
    <p>Keep attending events to climb the leaderboard! 🚀</p>

    <a href="{site}/dashboard/student/" class="btn">View My Dashboard →</a>
    """

    subject = f"🏆 Certificate of Participation — {event.title}"
    html    = _html_wrap("Your Certificate is Ready!", body, accent='#ffd93d')

    attachments = []
    if registration.certificate:
        try:
            attachments.append(registration.certificate.path)
        except Exception:
            pass

    _send_html_email(subject, student.email, html, attachments)
    registration.certificate_sent = True
    registration.save(update_fields=['certificate_sent'])


# ─────────────────────────────────────────────────────────────────────
#  5. EVENT APPROVAL / REJECTION EMAILS (to organizer)
# ─────────────────────────────────────────────────────────────────────

def send_event_approved_email(event):
    """Notify organizer their event was approved."""
    name = event.organizer.get_full_name() or event.organizer.username
    site = settings.SITE_URL

    body = f"""
    <div class="success-icon">✅</div>
    <h2>Your event is approved!</h2>
    <p>Hi {name.split()[0]}, great news — <strong>{event.title}</strong> has been approved by the admin and is now live for students to register.</p>

    <div class="info-box">
      <div><span class="info-label">🎫 Event</span> {event.title}</div>
      <div><span class="info-label">📅 Date</span> {event.date.strftime('%B %d, %Y')}</div>
      <div><span class="info-label">📍 Venue</span> {event.venue}</div>
      <div><span class="info-label">👥 Capacity</span> {event.max_capacity} seats</div>
    </div>

    <p>Students can now discover and register for your event. Share the link with your department!</p>
    <a href="{site}/events/{event.pk}/" class="btn">View Your Event →</a>
    """

    subject = f"✅ Event Approved: {event.title}"
    html    = _html_wrap("Event Approved", body, accent='#06d6a0')
    _send_html_email(subject, event.organizer.email, html)


def send_event_rejected_email(event):
    """Notify organizer their event was rejected."""
    name = event.organizer.get_full_name() or event.organizer.username
    site = settings.SITE_URL

    body = f"""
    <div class="success-icon">❌</div>
    <h2>Event Not Approved</h2>
    <p>Hi {name.split()[0]}, unfortunately <strong>{event.title}</strong> was not approved at this time.</p>

    <div class="info-box">
      <div><span class="info-label">🎫 Event</span> {event.title}</div>
      <div><span class="info-label">📋 Reason</span> {event.rejection_reason or 'No reason provided.'}</div>
    </div>

    <p>You can edit your event to address the concerns and resubmit for approval from your dashboard.</p>
    <a href="{site}/dashboard/organizer/" class="btn">Go to My Dashboard →</a>
    """

    subject = f"❌ Event Rejected: {event.title}"
    html    = _html_wrap("Event Not Approved", body, accent='#ff6b6b')
    _send_html_email(subject, event.organizer.email, html)


# ─────────────────────────────────────────────────────────────────────
#  PDF CERTIFICATE GENERATION
# ─────────────────────────────────────────────────────────────────────

def generate_certificate(registration):
    """Generate a landscape PDF certificate with gold-border design."""
    try:
        buffer = BytesIO()
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))

        # Navy background
        c.setFillColorRGB(0.05, 0.10, 0.25)
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

        # Gold double border
        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        c.setLineWidth(8)
        c.rect(20, 20, page_width - 40, page_height - 40, fill=0, stroke=1)
        c.setLineWidth(2)
        c.rect(30, 30, page_width - 60, page_height - 60, fill=0, stroke=1)

        # Title
        c.setFillColorRGB(0.85, 0.65, 0.13)
        c.setFont("Helvetica-Bold", 38)
        c.drawCentredString(page_width / 2, page_height - 100, "CERTIFICATE OF PARTICIPATION")
        c.setLineWidth(1.5)
        c.line(page_width * 0.2, page_height - 115, page_width * 0.8, page_height - 115)

        # Body text
        c.setFillColorRGB(0.85, 0.85, 0.85)
        c.setFont("Helvetica", 18)
        c.drawCentredString(page_width / 2, page_height - 165, "This is to certify that")

        student_name = registration.student.get_full_name() or registration.student.username
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(page_width / 2, page_height - 215, student_name)

        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        name_width = c.stringWidth(student_name, "Helvetica-Bold", 34)
        c.line(page_width/2 - name_width/2, page_height-225, page_width/2 + name_width/2, page_height-225)

        c.setFillColorRGB(0.85, 0.85, 0.85)
        c.setFont("Helvetica", 18)
        c.drawCentredString(page_width / 2, page_height - 265, "has successfully participated in")

        c.setFillColorRGB(0.85, 0.65, 0.13)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(page_width / 2, page_height - 305, registration.event.title)

        c.setFillColorRGB(0.75, 0.75, 0.75)
        c.setFont("Helvetica", 15)
        event_date = registration.event.date.strftime('%B %d, %Y')
        c.drawCentredString(page_width/2, page_height-345,
                            f"held on {event_date} at {registration.event.venue}")

        # Category badge
        c.setFillColorRGB(0.15, 0.30, 0.55)
        c.roundRect(page_width/2 - 60, page_height-390, 120, 28, 6, fill=1, stroke=0)
        c.setFillColorRGB(0.85, 0.65, 0.13)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width/2, page_height-380, registration.event.category.upper())

        # Signature
        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        c.setLineWidth(1)
        sig_x = page_width * 0.65
        c.line(sig_x-80, page_height-450, sig_x+80, page_height-450)
        c.setFillColorRGB(0.75, 0.75, 0.75)
        c.setFont("Helvetica", 12)
        org_name = registration.event.organizer.get_full_name() or registration.event.organizer.username
        c.drawCentredString(sig_x, page_height-465, org_name)
        c.drawCentredString(sig_x, page_height-478, "Event Organizer")

        # Footer
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width/2, 45,
                            "CampusEvents Platform | Certificate ID: " + registration.qr_token[:12])

        c.save()
        buffer.seek(0)
        filename = f"certificate_{registration.qr_token[:8]}.pdf"
        registration.certificate.save(filename, ContentFile(buffer.read()), save=True)
        return True
    except Exception as e:
        print(f"[Certificate Error] {e}")
        return False


# ─────────────────────────────────────────────────────────────────────
#  IN-APP NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────

def create_notification(user, title, message, notification_type='general', link=''):
    """Create an in-app notification for a user."""
    from events.models import Notification
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
    )


# ─────────────────────────────────────────────────────────────────────
#  EVENT RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────

def get_event_recommendations(student, limit=5):
    """Recommend events based on student's past registration categories."""
    from events.models import Event, Registration

    registered_categories = Registration.objects.filter(
        student=student
    ).values_list('event__category', flat=True).distinct()

    registered_event_ids = Registration.objects.filter(
        student=student
    ).values_list('event_id', flat=True)

    qs = Event.objects.filter(
        status='approved',
        date__gte=timezone.now().date()
    ).exclude(id__in=registered_event_ids)

    if registered_categories:
        qs = qs.filter(category__in=registered_categories)

    return qs.order_by('date')[:limit]
