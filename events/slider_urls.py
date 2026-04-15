from django.urls import path
from . import slider_views

urlpatterns = [
    path('',              slider_views.slider_list,   name='slider_list'),
    path('create/',       slider_views.slider_create, name='slider_create'),
    path('<int:pk>/edit/',   slider_views.slider_edit,   name='slider_edit'),
    path('<int:pk>/delete/', slider_views.slider_delete, name='slider_delete'),
    path('<int:pk>/toggle/', slider_views.slider_toggle, name='slider_toggle'),
    path('reorder/',      slider_views.slider_reorder, name='slider_reorder'),
    path('data/',         slider_views.public_slider_data, name='slider_data'),
]
