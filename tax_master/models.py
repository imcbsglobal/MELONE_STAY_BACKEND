from django.db import models


class IndiaTax(models.Model):
    client_id = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, blank=True, default="")
    cgst = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    sgst = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    igst = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    gst = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cal_method = models.CharField(max_length=50)
    status = models.CharField(max_length=10, default="ACTIVE")

    class Meta:
        db_table = "melonestay_india_tax"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "code"],
                name="unique_india_tax_code_per_client",
            ),
            models.UniqueConstraint(
                fields=["client_id", "name"],
                name="unique_india_tax_name_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class OtherTax(models.Model):
    client_id = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    tax = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    cal_method = models.CharField(max_length=50)
    status = models.CharField(max_length=10, default="ACTIVE")

    class Meta:
        db_table = "melonestay_other_tax"
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_id", "code"],
                name="unique_other_tax_code_per_client",
            ),
            models.UniqueConstraint(
                fields=["client_id", "name"],
                name="unique_other_tax_name_per_client",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"
