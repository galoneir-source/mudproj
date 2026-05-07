"""
web/api/urls.py

Rutas de la API REST del juego.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("status/",        views.api_status,      name="api-status"),
    path("who/",           views.api_who,          name="api-who"),
    path("rooms/",         views.api_rooms,        name="api-rooms"),
    path("rooms/<int:dbref>/", views.api_room_detail, name="api-room-detail"),
]
