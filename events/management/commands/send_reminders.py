"""
Management command: send_reminders
Sends reminder emails to students registered for events happening tomorrow.
Usage: python manage.py send_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from events.models import Registration
from events.utils import send_event_reminder


class Command(BaseCommand):
    help = 'Send reminder emails to students for events happening tomorrow'

    def handle(self, *args, **kwargs):
        tomorrow = timezone.now().date() + timedelta(days=1)
        registrations = Registration.objects.filter(
            event__date=tomorrow,
            event__status='approved',
            attended=False,
        ).select_related('student', 'event')

        count = 0
        for reg in registrations:
            try:
                send_event_reminder(reg)
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  Reminder sent -> {reg.student.email} for "{reg.event.title}"')
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed for {reg.student.email}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\nDone. {count} reminder(s) sent for {tomorrow}.'))
