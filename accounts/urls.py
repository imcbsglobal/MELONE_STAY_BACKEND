from django.urls import path
from . import views

urlpatterns = [
    path("superuser-login/", views.superuser_login, name="superuser_login"),
    path("fetch-client/", views.fetch_client, name="fetch_client"),
    path("create-admin/", views.create_admin, name="create_admin"),
    path("list-admins/", views.list_admins, name="list_admins"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("check-member-status/", views.check_member_status, name="check_member_status"),
    path("delete-admin/", views.delete_admin, name="delete_admin"),
    path("edit-admin/", views.edit_admin, name="edit_admin"),
]
