# Generated by Django 5.1.5 on 2025-01-19 15:33

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PatientData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=250)),
                ("patient_mobile_number", models.CharField(max_length=15, unique=True)),
                ("age", models.IntegerField()),
                ("gender", models.CharField(max_length=6)),
            ],
        ),
        migrations.CreateModel(
            name="PatientDeviceData",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                ("doctor_id", models.CharField(max_length=50)),
                ("patient_mobile_number", models.CharField(max_length=15)),
                ("device_serial_number", models.CharField(max_length=50)),
                (
                    "co",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "co2",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                (
                    "o2",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("heart_rate", models.IntegerField(blank=True, null=True)),
                (
                    "spo2",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("nh3", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ModelOutput",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "input_text",
                    models.TextField(help_text="Input text provided to the LLM"),
                ),
                (
                    "output_text",
                    models.TextField(help_text="Output text generated by the LLM"),
                ),
                (
                    "doctor_remark",
                    models.TextField(help_text="Doctor's remark", null=True),
                ),
                (
                    "doctor_comment",
                    models.TextField(help_text="Doctor's comment", null=True),
                ),
                ("doctor_note", models.TextField(help_text="Doctor's note", null=True)),
                ("patient_mobile_number", models.CharField(max_length=15)),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, help_text="Time when the record was created"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True, help_text="Time when the record was last updated"
                    ),
                ),
                (
                    "sensor_data",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.patientdevicedata",
                    ),
                ),
            ],
        ),
    ]
