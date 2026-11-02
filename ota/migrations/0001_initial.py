from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OTA",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("client_id", models.CharField(max_length=50)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=50)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name", "id"]},
        ),
        migrations.AddConstraint(
            model_name="ota",
            constraint=models.UniqueConstraint(
                fields=("client_id", "name"),
                name="unique_ota_name_per_client",
            ),
        ),
        migrations.AddConstraint(
            model_name="ota",
            constraint=models.UniqueConstraint(
                fields=("client_id", "code"),
                name="unique_ota_code_per_client",
            ),
        ),
    ]
