"""
Utility functions - Email notifications, PDF certificate generation
"""
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.core.files.base import ContentFile
import os
from io import BytesIO


def send_registration_email(registration):
    """Send registration confirmation email with QR code."""
    try:
        subject = f"✅ Registration Confirmed: {registration.event.title}"
        message = f"""
Hi {registration.student.get_full_name() or registration.student.username},

Your registration for "{registration.event.title}" is confirmed!

📅 Date: {registration.event.date.strftime('%B %d, %Y')}
⏰ Time: {registration.event.start_time.strftime('%I:%M %p')} - {registration.event.end_time.strftime('%I:%M %p')}
📍 Venue: {registration.event.venue}

Your unique QR code is attached. Please bring it on event day for attendance.

See you there! 🎉
Campus Events Team
        """
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.student.email],
        )
        
        # Attach QR code if it exists
        if registration.qr_code:
            qr_path = registration.qr_code.path
            if os.path.exists(qr_path):
                email.attach_file(qr_path)
        
        email.send(fail_silently=True)
    except Exception as e:
        print(f"Email error: {e}")


def send_event_reminder(registration):
    """Send event reminder email."""
    try:
        subject = f"⏰ Reminder: {registration.event.title} is Tomorrow!"
        message = f"""
Hi {registration.student.get_full_name() or registration.student.username},

Just a reminder that "{registration.event.title}" is happening tomorrow!

📅 Date: {registration.event.date.strftime('%B %d, %Y')}
⏰ Time: {registration.event.start_time.strftime('%I:%M %p')}
📍 Venue: {registration.event.venue}

Don't forget your QR code for attendance!

See you there! 🎉
Campus Events Team
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [registration.student.email], fail_silently=True)
    except Exception as e:
        print(f"Reminder email error: {e}")


def generate_certificate(registration):
    """Generate a PDF certificate for event attendance using ReportLab."""
    try:
        buffer = BytesIO()
        
        # Use landscape A4
        page_width, page_height = landscape(A4)
        c = canvas.Canvas(buffer, pagesize=landscape(A4))
        
        # ── Background gradient (simulated with rectangles) ──
        c.setFillColorRGB(0.05, 0.10, 0.25)  # Deep navy
        c.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        
        # Gold border
        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        c.setLineWidth(8)
        c.rect(20, 20, page_width - 40, page_height - 40, fill=0, stroke=1)
        c.setLineWidth(2)
        c.rect(30, 30, page_width - 60, page_height - 60, fill=0, stroke=1)
        
        # ── Header ──
        c.setFillColorRGB(0.85, 0.65, 0.13)  # Gold
        c.setFont("Helvetica-Bold", 38)
        c.drawCentredString(page_width / 2, page_height - 100, "CERTIFICATE OF PARTICIPATION")
        
        # Subtitle line
        c.setLineWidth(1.5)
        c.line(page_width * 0.2, page_height - 115, page_width * 0.8, page_height - 115)
        
        # ── "This is to certify that" ──
        c.setFillColorRGB(0.85, 0.85, 0.85)
        c.setFont("Helvetica", 18)
        c.drawCentredString(page_width / 2, page_height - 165, "This is to certify that")
        
        # ── Student Name ──
        student_name = registration.student.get_full_name() or registration.student.username
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(page_width / 2, page_height - 215, student_name)
        
        # Name underline
        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        name_width = c.stringWidth(student_name, "Helvetica-Bold", 34)
        c.line(
            page_width / 2 - name_width / 2, page_height - 225,
            page_width / 2 + name_width / 2, page_height - 225
        )
        
        # ── "has successfully participated in" ──
        c.setFillColorRGB(0.85, 0.85, 0.85)
        c.setFont("Helvetica", 18)
        c.drawCentredString(page_width / 2, page_height - 265, "has successfully participated in")
        
        # ── Event Name ──
        c.setFillColorRGB(0.85, 0.65, 0.13)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(page_width / 2, page_height - 305, registration.event.title)
        
        # ── Event Date and Venue ──
        c.setFillColorRGB(0.75, 0.75, 0.75)
        c.setFont("Helvetica", 15)
        event_date = registration.event.date.strftime('%B %d, %Y')
        c.drawCentredString(
            page_width / 2, page_height - 345,
            f"held on {event_date} at {registration.event.venue}"
        )
        
        # ── Category badge ──
        c.setFillColorRGB(0.15, 0.30, 0.55)
        badge_x = page_width / 2 - 60
        c.roundRect(badge_x, page_height - 390, 120, 28, 6, fill=1, stroke=0)
        c.setFillColorRGB(0.85, 0.65, 0.13)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(page_width / 2, page_height - 380,
                            registration.event.category.upper())
        
        # ── Organizer signature area ──
        c.setStrokeColorRGB(0.85, 0.65, 0.13)
        c.setLineWidth(1)
        sig_x = page_width * 0.65
        c.line(sig_x - 80, page_height - 450, sig_x + 80, page_height - 450)
        c.setFillColorRGB(0.75, 0.75, 0.75)
        c.setFont("Helvetica", 12)
        organizer_name = registration.event.organizer.get_full_name() or registration.event.organizer.username
        c.drawCentredString(sig_x, page_height - 465, organizer_name)
        c.drawCentredString(sig_x, page_height - 478, "Event Organizer")
        
        # ── College name ──
        c.setFillColorRGB(0.5, 0.5, 0.5)
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_width / 2, 45, "Campus Event Management System | Certificate ID: " + registration.qr_token[:12])
        
        c.save()
        buffer.seek(0)
        
        filename = f"certificate_{registration.qr_token[:8]}.pdf"
        registration.certificate.save(filename, ContentFile(buffer.read()), save=True)
        return True
    except Exception as e:
        print(f"Certificate generation error: {e}")
        return False


def send_certificate_email(registration):
    """Send certificate via email."""
    try:
        subject = f"🏆 Your Certificate for {registration.event.title}"
        message = f"""
Hi {registration.student.get_full_name() or registration.student.username},

Congratulations on attending "{registration.event.title}"!

Your certificate of participation is attached to this email.

Keep participating and keep growing! 🌟
Campus Events Team
        """
        
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[registration.student.email],
        )
        
        if registration.certificate:
            cert_path = registration.certificate.path
            if os.path.exists(cert_path):
                email.attach_file(cert_path)
        
        email.send(fail_silently=True)
        registration.certificate_sent = True
        registration.save()
    except Exception as e:
        print(f"Certificate email error: {e}")


def create_notification(user, title, message, notification_type='general'):
    """Create an in-app notification."""
    from events.models import Notification
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )


def get_event_recommendations(student, limit=5):
    """Recommend events based on student's registration history."""
    from events.models import Event, Registration
    from django.utils import timezone
    
    # Get categories the student has registered for
    registered_categories = Registration.objects.filter(
        student=student
    ).values_list('event__category', flat=True).distinct()
    
    # Get events the student hasn't registered for
    registered_event_ids = Registration.objects.filter(
        student=student
    ).values_list('event_id', flat=True)
    
    if registered_categories:
        # Recommend based on past categories
        recommendations = Event.objects.filter(
            category__in=registered_categories,
            status='approved',
            date__gte=timezone.now().date()
        ).exclude(id__in=registered_event_ids).order_by('date')[:limit]
    else:
        # New student — show all upcoming events
        recommendations = Event.objects.filter(
            status='approved',
            date__gte=timezone.now().date()
        ).exclude(id__in=registered_event_ids).order_by('date')[:limit]
    
    return recommendations
