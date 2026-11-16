from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("requests", "0005_rename_borrowerrequest_borrowrequest")]

    operations = [
        migrations.AddField(
            model_name="borrowrequest",
            name="return_condition",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="borrowrequest",
            name="returned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="borrowrequest",
            name="status",
            field=models.CharField(
                max_length=20,
                default="PENDING",
                choices=[
                    ("PENDING", "Pending"),
                    ("APPROVED", "Approved"),
                    ("REJECTED", "Rejected"),
                    ("CANCELLED", "Cancelled"),
                    ("CHECKED_OUT", "Checked Out"),
                    ("RETURNED", "Returned"),
                    ("COMPLETED", "Completed"),
                ],
            ),
        ),
    ]
