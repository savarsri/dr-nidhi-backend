# Generated by Django 5.0 on 2025-03-04 17:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_rename_designation_customuser_medication"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patientdevicedata",
            name="o2_delta",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="patientdevicedata",
            name="rq",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]
