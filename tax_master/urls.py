from django.urls import path

from . import views

urlpatterns = [
    path("india/", views.india_list_create_update, name="india_tax_list_create_update"),
    path("india/<int:pk>/", views.india_detail_delete, name="india_tax_detail_delete"),
    path("other/", views.other_list_create_update, name="other_tax_list_create_update"),
    path("other/<int:pk>/", views.other_detail_delete, name="other_tax_detail_delete"),
]
