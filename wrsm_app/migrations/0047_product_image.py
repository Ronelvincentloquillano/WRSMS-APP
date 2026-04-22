from django.db import migrations, models
import wrsm_app.models


class Migration(migrations.Migration):

    dependencies = [
        ("wrsm_app", "0046_order_order_type_no_invalid_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image",
            field=models.ImageField(
                blank=True, null=True, upload_to=wrsm_app.models.station_image_upload_path
            ),
        ),
    ]
