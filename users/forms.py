"""
Users app forms - Registration and login forms
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class StudentRegistrationForm(UserCreationForm):
    """Form for student registration."""
    
    first_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    department = forms.CharField(max_length=100, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Computer Science'}))
    roll_number = forms.CharField(max_length=20, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Roll Number'}))
    year_of_study = forms.IntegerField(min_value=1, max_value=5, required=False,
        widget=forms.NumberInput(attrs={'placeholder': 'Year (1-4)'}))
    phone = forms.CharField(max_length=15, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email',
                  'department', 'roll_number', 'year_of_study', 'phone',
                  'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
        return user


class OrganizerRegistrationForm(UserCreationForm):
    """Form for event organizer (club head) registration."""
    
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    department = forms.CharField(max_length=100, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Club / Department'}))
    phone = forms.CharField(max_length=15, required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'About your club...'}),
        required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email',
                  'department', 'phone', 'bio', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'organizer'
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Custom login form."""
    username = forms.CharField(widget=forms.TextInput(
        attrs={'placeholder': 'Username', 'autofocus': True}))
    password = forms.CharField(widget=forms.PasswordInput(
        attrs={'placeholder': 'Password'}))


class ProfileUpdateForm(forms.ModelForm):
    """Form to update user profile."""
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'department',
                  'phone', 'bio', 'profile_pic', 'roll_number', 'year_of_study']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }
