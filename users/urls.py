from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/organizer/', views.register_organizer, name='register_organizer'),
    path('profile/', views.profile, name='profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('manage/', views.admin_user_list, name='user_list'),
]
