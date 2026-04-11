"""campus_events URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),
    path('events/', include('events.urls')),
    path('', lambda request: redirect('dashboard'), name='home'),
    path('dashboard/', include('events.dashboard_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
