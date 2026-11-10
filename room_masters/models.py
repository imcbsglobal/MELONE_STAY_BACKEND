from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from room_categories.models import RoomCategory


class Room(models.Model):
    AIR_CONDITIONING_CHOICES = [
        ("AC", "AC"),
        ("Non-AC", "Non-AC"),
    ]

    client_id = models.CharField(max_length=50)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=120)
    category = models.ForeignKey(
        RoomCategory,
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    air_conditioning = models.CharField(
        max_length=10,
        choices=AIR_CONDITIONING_CHOICES,
        default="AC",
    )
    floor = models.CharField(max_length=60)
    tax = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "melonestay_room"
        ordering = ["code", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "code"],
                name="unique_room_code_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class RoomPrice(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="prices")
    name = models.CharField(max_length=60)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "melonestay_roomprice"
        ordering = ["id"]

    def __str__(self):
        return f"{self.room.code}: {self.name}"
