from django.db import models


class Currency(models.Model):
    client_id = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, default="ACTIVE")

    class Meta:
        db_table = "melonestay_currency"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "code"],
                name="unique_currency_code_per_client",
            ),
            models.UniqueConstraint(
                fields=["client_id", "name"],
                name="unique_currency_name_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
