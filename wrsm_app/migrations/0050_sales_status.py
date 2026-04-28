from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wrsm_app', '0049_create_station_user_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='sales',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('Pending', 'Pending'),
                    ('In Progress', 'In Progress'),
                    ('Completed', 'Completed'),
                    ('Cancelled', 'Cancelled'),
                ],
                default='Completed',
                max_length=50,
                null=True,
            ),
        ),
    ]
