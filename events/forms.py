"""
Events app forms - fixed validation, proper error handling
"""
from django import forms
from django.utils import timezone
from .models import Event, Feedback


class EventForm(forms.ModelForm):
    """Form for creating/editing events. All fields validated server-side."""

    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    end_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )
    # Make is_paid and fee optional at the form level — validate in clean()
    is_paid = forms.BooleanField(required=False)
    registration_fee = forms.DecimalField(
        required=False, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
    )
    # Make certificate_template optional
    certificate_template = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 'rows': 2,
            'placeholder': 'This is to certify that {student_name} participated in {event_name} on {event_date}.'
        }),
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category',
            'date', 'start_time', 'end_time',
            'venue', 'max_capacity', 'poster',
            'is_paid', 'registration_fee', 'certificate_template',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. Annual Tech Fest 2024',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Describe your event...',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'venue': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Main Auditorium',
            }),
            'max_capacity': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': '100',
                'min': 1, 'max': 10000,
            }),
        }

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get('start_time')
        end_time   = cleaned.get('end_time')
        date       = cleaned.get('date')
        venue      = cleaned.get('venue', '').strip()
        is_paid    = cleaned.get('is_paid', False)
        fee        = cleaned.get('registration_fee')

        # 1. End time must be after start time
        if start_time and end_time and end_time <= start_time:
            self.add_error('end_time', 'End time must be after start time.')

        # 2. Paid event must have a fee > 0
        if is_paid and (fee is None or fee <= 0):
            self.add_error('registration_fee',
                           'Please enter a registration fee greater than ₹0 for a paid event.')

        # 3. Free event: zero out the fee
        if not is_paid:
            cleaned['registration_fee'] = 0

        # 4. Date must not be in the past
        if date and date < timezone.now().date():
            self.add_error('date', 'Event date cannot be in the past.')

        # 5. Venue clash detection
        if date and start_time and end_time and venue:
            clashing = Event.objects.filter(
                date=date,
                venue__iexact=venue,
                status__in=['approved', 'pending'],
            )
            if self.instance.pk:
                clashing = clashing.exclude(pk=self.instance.pk)

            for ev in clashing:
                # Time overlap check
                if not (end_time <= ev.start_time or start_time >= ev.end_time):
                    self.add_error(None,
                        f'⚠️ Venue clash: "{ev.title}" is already at {venue} '
                        f'from {ev.start_time.strftime("%I:%M %p")} to '
                        f'{ev.end_time.strftime("%I:%M %p")} on {date.strftime("%b %d")}.'
                    )

        return cleaned

    def save(self, commit=True):
        event = super().save(commit=False)
        # Default certificate template if left blank
        if not event.certificate_template:
            event.certificate_template = (
                'This is to certify that {student_name} has successfully '
                'participated in {event_name} held on {event_date}.'
            )
        if commit:
            event.save()
        return event


class FeedbackForm(forms.ModelForm):
    """Form for event feedback."""

    rating = forms.ChoiceField(
        choices=[(i, f'{i} Star{"s" if i > 1 else ""}') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating-input'}),
    )

    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience...',
                'class': 'form-control',
            }),
        }


class EventSearchForm(forms.Form):
    """Event search and filter form."""

    CATEGORY_CHOICES = [('', 'All Categories')] + Event.CATEGORY_CHOICES

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '🔍 Search events...',
        }),
    )
    category  = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False,
                                   widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = forms.DateField(required=False,
                                 widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_to   = forms.DateField(required=False,
                                 widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))