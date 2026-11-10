from django.db import models


class OTA(models.Model):
    client_id = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "melonestay_ota"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "name"],
                name="unique_ota_name_per_client",
            ),
            models.UniqueConstraint(
                fields=["client_id", "code"],
                name="unique_ota_code_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
