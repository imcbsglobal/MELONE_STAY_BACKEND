from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def hash_legacy_passwords(apps, schema_editor):
    AdminAccount = apps.get_model("accounts", "AdminAccount")
    for admin in AdminAccount.objects.all().iterator():
        try:
            identify_hasher(admin.password)
        except ValueError:
            admin.password = make_password(admin.password)
            admin.save(update_fields=["password"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(hash_legacy_passwords, migrations.RunPython.noop),
    ]
