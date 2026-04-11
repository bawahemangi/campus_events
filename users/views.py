"""
Users app views - Authentication, registration, profile
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from .forms import StudentRegistrationForm, OrganizerRegistrationForm, ProfileUpdateForm
from .models import CustomUser


def register_student(request):
    """Student registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your student account is ready.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = StudentRegistrationForm()
    
    return render(request, 'users/register_student.html', {'form': form})


def register_organizer(request):
    """Organizer registration view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = OrganizerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your organizer account is ready.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = OrganizerRegistrationForm()
    
    return render(request, 'users/register_organizer.html', {'form': form})


def user_login(request):
    """Login view."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', '')
            return redirect(next_url if next_url else 'dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'users/login.html', {})


def user_logout(request):
    """Logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def profile(request):
    """User profile view."""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    # Get user stats
    from events.models import Registration
    registrations = Registration.objects.filter(student=request.user)
    attended_count = registrations.filter(attended=True).count()
    registered_count = registrations.count()
    
    context = {
        'form': form,
        'attended_count': attended_count,
        'registered_count': registered_count,
        'points': request.user.participation_points,
    }
    return render(request, 'users/profile.html', context)


@login_required
def leaderboard(request):
    """Participation leaderboard."""
    top_students = CustomUser.objects.filter(role='student').order_by(
        '-participation_points')[:20]
    
    # Annotate with registration count
    students_data = []
    for i, student in enumerate(top_students, 1):
        from events.models import Registration
        reg_count = Registration.objects.filter(student=student, attended=True).count()
        students_data.append({
            'rank': i,
            'student': student,
            'events_attended': reg_count,
            'points': student.participation_points,
        })
    
    return render(request, 'users/leaderboard.html', {'students_data': students_data})


@login_required
def admin_user_list(request):
    """Admin view to list all users."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    users = CustomUser.objects.all().order_by('role', 'username')
    context = {'users': users}
    return render(request, 'users/user_list.html', context)
