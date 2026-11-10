from django.urls import path
from . import views

urlpatterns = [
    path("superuser-login/", views.superuser_login, name="superuser_login"),
    path("fetch-client/", views.fetch_client, name="fetch_client"),
    path("create-admin/", views.create_admin, name="create_admin"),
    path("list-admins/", views.list_admins, name="list_admins"),
    path("list-signup-users/", views.list_signup_users, name="list_signup_users"),
    path("admin-login/", views.admin_login, name="admin_login"),
    path("check-member-status/", views.check_member_status, name="check_member_status"),
    path("delete-admin/", views.delete_admin, name="delete_admin"),
    path("edit-admin/", views.edit_admin, name="edit_admin"),
    path("delete-demo-user/", views.delete_demo_user, name="delete_demo_user"),
    path("edit-demo-user/", views.edit_demo_user, name="edit_demo_user"),
    path("signup/", views.signup, name="signup"),
    path("superuser-credentials/", views.superuser_credentials, name="superuser_credentials"),
    path("countries/", views.countries_proxy, name="countries_proxy"),
    path("activity-log/", views.activity_log_proxy, name="activity_log_proxy"),
    path("activity-log/create/", views.activity_log_create_proxy, name="activity_log_create_proxy"),
    path("user-master/", views.user_master_proxy, name="user_master_list_create"),
    path("user-master/<int:pk>/", views.user_master_proxy, name="user_master_detail"),
]
