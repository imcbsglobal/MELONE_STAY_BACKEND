from django.urls import path

from . import views

urlpatterns = [
    path("currencies/", views.currency_list_create_update, name="currency_list_create_update"),
    path("currencies/<int:pk>/", views.currency_detail_delete, name="currency_detail_delete"),
]
