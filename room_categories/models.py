from django.db import models


class RoomCategory(models.Model):
    client_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "melonestay_roomcategory"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "name"],
                name="unique_room_category_name_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.client_id})"
