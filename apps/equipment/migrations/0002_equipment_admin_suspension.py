from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("equipment", "0001_initial")]
    operations = [
        migrations.AddField(model_name="equipment", name="admin_suspended", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="equipment", name="admin_suspension_reason", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="equipment", name="admin_suspended_at", field=models.DateTimeField(blank=True, null=True)),
    ]
