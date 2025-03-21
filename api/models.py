from django.db import models

class PatientDeviceData(models.Model):
    id = models.AutoField(primary_key=True)
    doctor_id = models.CharField(max_length=50)
    patient_mobile_number = models.CharField(max_length=15)
    device_serial_number = models.CharField(max_length=50)
    co = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    co2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    o2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    spo2 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nh3 = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PatientDeviceData(id={self.id}, doctor_id={self.doctor_id}, device_serial_number={self.device_serial_number})"

class PatientData(models.Model):
    name = models.CharField(max_length=250, null=False, blank=False)
    patient_mobile_number = models.CharField(max_length=15, unique=True)
    age = models.IntegerField(null=False, blank=False)
    gender = models.CharField(max_length=6,null=False, blank=False)

class ModelOutput(models.Model):
    input_text = models.TextField(help_text="Input text provided to the LLM", null=False, blank=False)
    output_text = models.TextField(help_text="Output text generated by the LLM", null=False, blank=False)
    doctor_remark = models.TextField(help_text="Doctor's remark", null=True)
    doctor_comment = models.TextField(help_text="Doctor's comment", null=True)
    doctor_note = models.TextField(help_text="Doctor's note", null=True)
    sensor_data = models.ForeignKey(PatientDeviceData, on_delete=models.CASCADE, null=False, blank=False)
    patient_mobile_number = models.CharField(max_length=15, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, help_text="Time when the record was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Time when the record was last updated")