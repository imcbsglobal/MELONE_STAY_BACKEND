from django.db import models


class AdminAccount(models.Model):
    client_id = models.CharField(max_length=50)
    customer_name = models.CharField(max_length=200)
    license_key = models.CharField(max_length=50)
    package = models.CharField(max_length=50)
    module_name = models.CharField(max_length=200, blank=True, default="")
    expiry_date = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(max_length=20, blank=True, default="Active")
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    # Field to distinguish between admin-created users and signup users
    is_demo_user = models.BooleanField(default=False)
    # Financial year field
    financial_year = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        db_table = "melonestay_adminaccount"

    def __str__(self):
        return f"{self.username} ({self.customer_name})"
