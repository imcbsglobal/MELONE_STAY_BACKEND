from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.list_categories, name="list_room_categories"),
    path("create/", views.create_category, name="create_room_category"),
    path("edit/", views.edit_category, name="edit_room_category"),
    path("delete/", views.delete_category, name="delete_room_category"),
]
