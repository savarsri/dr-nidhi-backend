# Generated by Django 5.0 on 2025-03-04 19:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_alter_patientdevicedata_o2_delta_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="llmoutput",
            name="file_urls",
            field=models.JSONField(default=list),
        ),
    ]
