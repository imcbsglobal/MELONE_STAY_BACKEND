from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.list_rooms, name="list_rooms"),
    path("create/", views.create_room, name="create_room"),
    path("edit/", views.edit_room, name="edit_room"),
    path("delete/", views.delete_room, name="delete_room"),
    path("favorite/", views.set_room_favorite, name="set_room_favorite"),
]
