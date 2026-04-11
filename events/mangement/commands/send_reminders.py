"""
Management command to send event reminder emails.
Run daily via cron: python manage.py send_reminders

  crontab: 0 8 * * * /path/to/venv/bin/python /path/to/manage.py send_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from events.models import Registration
from events.utils import send_event_reminder, create_notification


class Command(BaseCommand):
    help = 'Send reminder emails + in-app notifications for events happening tomorrow'

    def handle(self, *args, **kwargs):
        tomorrow = timezone.now().date() + timedelta(days=1)

        registrations = Registration.objects.filter(
            event__date=tomorrow,
            event__status='approved',
            attended=False,
        ).select_related('student', 'event')

        self.stdout.write(f"Found {registrations.count()} registrations for tomorrow ({tomorrow})")

        sent = 0
        for reg in registrations:
            try:
                # Send reminder email
                send_event_reminder(reg)

                # Create in-app notification
                create_notification(
                    reg.student,
                    f"⏰ Tomorrow: {reg.event.title}",
                    f"Don't forget! {reg.event.title} is tomorrow at {reg.event.start_time.strftime('%I:%M %p')} — {reg.event.venue}",
                    'reminder',
                    link=f'/events/{reg.event.pk}/'
                )

                sent += 1
                self.stdout.write(f"  ✅ Sent reminder to {reg.student.username} for {reg.event.title}")
            except Exception as e:
                self.stdout.write(f"  ❌ Failed for {reg.student.username}: {e}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Done — {sent} reminders sent."))
