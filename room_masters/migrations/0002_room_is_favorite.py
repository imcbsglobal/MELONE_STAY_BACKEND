from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("room_masters", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="is_favorite",
            field=models.BooleanField(default=False),
        ),
    ]
