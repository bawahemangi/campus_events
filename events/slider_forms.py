"""
SliderItem form for admin create/edit.
"""
from django import forms
from .models import SliderItem, Event


class SliderItemForm(forms.ModelForm):
    class Meta:
        model  = SliderItem
        fields = [
            'title', 'subtitle', 'image', 'slide_type',
            'linked_event', 'cta_text', 'cta_url',
            'text_color', 'is_active', 'order',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Annual Tech Fest 2024',
            }),
            'subtitle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 48-hour hackathon · Feb 10 · Innovation Lab',
            }),
            'slide_type': forms.Select(attrs={'class': 'form-select'}),
            'linked_event': forms.Select(attrs={'class': 'form-select'}),
            'cta_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Register Now',
            }),
            'cta_url': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '/events/  (leave blank to auto-use linked event)',
            }),
            'text_color': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show approved events in the dropdown
        self.fields['linked_event'].queryset = Event.objects.filter(
            status='approved'
        ).order_by('-date')
        self.fields['linked_event'].empty_label = '— No linked event —'
        self.fields['linked_event'].required = False
        self.fields['subtitle'].required     = False
        self.fields['cta_text'].required     = False
        self.fields['cta_url'].required      = False
