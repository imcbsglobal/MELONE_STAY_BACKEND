from django.urls import path, include

urlpatterns = [
    path("api/", include("accounts.urls")),
    path("api/staffs/", include("staffs.urls")),
    path("api/room-categories/", include("room_categories.urls")),
    path("api/room-master/", include("room_masters.urls")),
    path("api/ota/", include("ota.urls")),
]
