"""
Events app forms
"""
from django import forms
from .models import Event, Feedback


class EventForm(forms.ModelForm):
    """Form for creating/editing events."""
    
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category', 'date', 'start_time',
            'end_time', 'venue', 'max_capacity', 'poster', 'certificate_template'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your event...'}),
            'certificate_template': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Use {student_name}, {event_name}, {event_date} as placeholders'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')
        venue = cleaned_data.get('venue')

        # Validate end time > start time
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")

        # Check for venue clashes (Event Clash Detection)
        if date and start_time and end_time and venue:
            clashing_events = Event.objects.filter(
                date=date,
                venue__iexact=venue,
                status__in=['approved', 'pending']
            )
            # Exclude current event if editing
            if self.instance.pk:
                clashing_events = clashing_events.exclude(pk=self.instance.pk)

            for event in clashing_events:
                # Check for time overlap
                if not (end_time <= event.start_time or start_time >= event.end_time):
                    raise forms.ValidationError(
                        f"⚠️ Venue Clash Detected! '{event.title}' is already scheduled at "
                        f"{venue} from {event.start_time.strftime('%I:%M %p')} to "
                        f"{event.end_time.strftime('%I:%M %p')} on {date}."
                    )

        return cleaned_data


class FeedbackForm(forms.ModelForm):
    """Form for event feedback."""
    
    rating = forms.ChoiceField(
        choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'star-rating-input'})
    )

    class Meta:
        model = Feedback
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Share your experience...'
            }),
        }


class EventSearchForm(forms.Form):
    """Event search and filter form."""
    
    CATEGORY_CHOICES = [('', 'All Categories')] + Event.CATEGORY_CHOICES
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '🔍 Search events...'})
    )
    category = forms.ChoiceField(choices=CATEGORY_CHOICES, required=False)
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
