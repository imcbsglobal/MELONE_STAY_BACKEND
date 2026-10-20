from django.urls import path
from . import views

urlpatterns = [
    path("list/", views.list_staffs, name="list_staffs"),
    path("create/", views.create_staff, name="create_staff"),
    path("delete/", views.delete_staff, name="delete_staff"),
    path("edit/", views.edit_staff, name="edit_staff"),
]