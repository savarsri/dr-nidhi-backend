from rest_framework import serializers
from .models import CustomUser, PatientDeviceData, PatientData, LLMOutput
from django.contrib.auth import get_user_model
from djoser import serializers as djoser_serializers

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
            'o2_delta',
            'rq',
            'hydrogen',
            'formaldehyde',
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

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    # Make sure the password is write-only.
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'full_name',
            'username',
            'email',
            'password',
            'medication',
            'phone_number',
            'role',  # You can choose to allow clients to set this or leave it read-only.
        )
        read_only_fields = ('id',)

    def create(self, validated_data):
        # Remove the password from the data and set it using set_password
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.email_verified = False
        user.save()
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # List only the fields that you want the user to update.
        fields = (
            'full_name',
            'medication',
            'phone_number',
            'role',
        )

class DjoserUserSerializer(djoser_serializers.UserSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'role']

class LLMOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMOutput
        fields = "__all__"  # Default to all fields

    def __init__(self, *args, **kwargs):
        # Get requested fields from context
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        # If specific fields are requested, limit the serializer fields
        if fields:
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)

class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.IntegerField()