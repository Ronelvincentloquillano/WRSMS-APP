from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('wrsm_app', '0038_notification'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ContainerInventory',
            new_name='ContainerManagement',
        ),
        migrations.AlterModelOptions(
            name='containermanagement',
            options={'verbose_name_plural': 'container management'},
        ),
        migrations.AlterField(
            model_name='containermanagement',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='container_management_created', to='wrsm_app.profile'),
        ),
        migrations.AlterField(
            model_name='containermanagement',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='containermanagement_modified_by', to='wrsm_app.profile'),
        ),
    ]