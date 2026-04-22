from django.db import migrations


ROLE_GROUPS = (
    'station owner/admin',
    'staff',
    'driver',
)


def forwards(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ROLE_GROUPS:
        Group.objects.get_or_create(name=name)


def backwards(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=('staff', 'driver')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('wrsm_app', '0048_shortcut_image'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

