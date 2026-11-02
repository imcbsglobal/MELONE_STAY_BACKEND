from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations


def hash_legacy_passwords(apps, schema_editor):
    Staff = apps.get_model("staffs", "Staff")
    for staff in Staff.objects.all().iterator():
        try:
            identify_hasher(staff.password)
        except ValueError:
            staff.password = make_password(staff.password)
            staff.save(update_fields=["password"])


class Migration(migrations.Migration):

    dependencies = [
        ("staffs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(hash_legacy_passwords, migrations.RunPython.noop),
    ]
