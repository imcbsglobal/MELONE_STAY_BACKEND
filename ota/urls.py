from django.urls import path

from . import views

urlpatterns = [
    path("list/", views.list_otas, name="list_otas"),
    path("create/", views.create_ota, name="create_ota"),
]
