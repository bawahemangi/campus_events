"""
Users app models - Custom User with role-based access
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Extended user model with role support."""
    
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('organizer', 'Event Organizer'),
        ('student', 'Student'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    
    # Student-specific fields
    roll_number = models.CharField(max_length=20, blank=True)
    year_of_study = models.IntegerField(null=True, blank=True)
    
    # Leaderboard points
    participation_points = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'
    
    @property
    def is_organizer(self):
        return self.role == 'organizer'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
