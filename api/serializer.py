from rest_framework import serializers
from .models import PatientDeviceData, PatientData

class PatientDeviceDataSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(read_only=True)
    patient_age = serializers.IntegerField(read_only=True)
    patient_gender = serializers.CharField(read_only=True)
    model_generated = serializers.BooleanField(read_only=True)
    model_output_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PatientDeviceData
        fields = [
            'id',
            'doctor_id',
            'patient_mobile_number',
            'device_serial_number',
            'co',
            'co2',
            'o2',
            'heart_rate',
            'spo2',
            'nh3',
            'created_at',
            'patient_name',
            'patient_age',
            'patient_gender',
            'model_generated',
            'model_output_id'
        ]

class PatientDataSerializer(serializers.ModelSerializer):

    class Meta:
        model = PatientData
        fields = '__all__'