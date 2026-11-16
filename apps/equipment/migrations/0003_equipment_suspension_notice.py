from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("equipment", "0002_equipment_admin_suspension"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="EquipmentSuspensionNotice",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("message", models.CharField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("equipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suspension_notices", to="equipment.equipment")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="equipment_notices", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
