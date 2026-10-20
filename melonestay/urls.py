from django.urls import path, include

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/staffs/", include("staffs.urls")),
]
