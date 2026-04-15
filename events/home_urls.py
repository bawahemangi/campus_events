from django.urls import path
from .home_views import homepage

urlpatterns = [
    path('', homepage, name='home'),
]
