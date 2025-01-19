from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db.models import OuterRef, Subquery, Exists
from django.shortcuts import get_object_or_404

from .models import PatientDeviceData, PatientData, ModelOutput
from .serializer import PatientDeviceDataSerializer, PatientDataSerializer
from .prompt import generate_prompt, send_to_grok_ai

class GenerateGrokResponse(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        sensor_data_id = request.data['id']
        patientName = request.data['name']
        phoneNumber = request.data['phone']
        age = request.data['age']
        gender = request.data['gender']
        symptoms = request.data['majorsymptoms']
        history = request.data['medicalHistory']
        medication_type = request.data['medication_type']

        patient, created = PatientData.objects.get_or_create(
            patient_mobile_number=phoneNumber,
            defaults={
                'name': patientName,
                'age': age,
                'gender': gender
            }
        )

        sensor_data = PatientDeviceData.objects.get(id=sensor_data_id)
        patientDeviceData = PatientDeviceDataSerializer(sensor_data)

        patient_data = {
            "patientName": patientName,
            "age": age,
            "gender": gender,
            "symptoms": symptoms,
            "medicalHistory": history,
        }

        prompt = generate_prompt(patient_data, patientDeviceData.data)
        grok_response = send_to_grok_ai(prompt, medication_type)

        model_output = ModelOutput.objects.create(
            input_text=prompt,
            output_text=grok_response,
            sensor_data=sensor_data,
            patient_mobile_number=phoneNumber
        )

        return Response({
            "model_output_id": model_output.id
        }, status=status.HTTP_200_OK)
    
class SinglePatientView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, id):
        patient = get_object_or_404(PatientData, patient_mobile_number=id)
        serializer = PatientDataSerializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)

    
class PatientView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):

        latest_records = PatientDeviceData.objects.filter(
                patient_mobile_number=OuterRef('patient_mobile_number')
                ).order_by('-created_at')

        unique_latest_records = PatientDeviceData.objects.filter(
            created_at=Subquery(latest_records.values('created_at')[:1])
        )

        model_output_exists = ModelOutput.objects.filter(
            sensor_data_id=OuterRef('id')
        )

        model_output_id = ModelOutput.objects.filter(
            sensor_data_id=OuterRef('id')
        ).values('id')[:1]

        result = unique_latest_records.annotate(
            patient_name=Subquery(
                PatientData.objects.filter(patient_mobile_number=OuterRef('patient_mobile_number')).values('name')[:1]
            ),
            patient_age=Subquery(
                PatientData.objects.filter(patient_mobile_number=OuterRef('patient_mobile_number')).values('age')[:1]
            ),
            patient_gender=Subquery(
                PatientData.objects.filter(patient_mobile_number=OuterRef('patient_mobile_number')).values('gender')[:1]
            ),
            model_generated=Exists(model_output_exists),
            # Add the id of the corresponding row in ModelOutput
            model_output_id=Subquery(model_output_id)
        ).values(
            'id', 'doctor_id', 'patient_mobile_number', 'device_serial_number',
            'co', 'co2', 'o2', 'heart_rate', 'spo2', 'nh3', 'created_at',
            'patient_name', 'patient_age', 'patient_gender', 'model_generated', 'model_output_id'
        )

        serializer = PatientDeviceDataSerializer(result, many=True)

        return Response(serializer.data,status=status.HTTP_200_OK)

class StatusView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, id):
        model_output = get_object_or_404(ModelOutput, id=id)

        sensor_data = model_output.sensor_data

        response_data = {
            "model_output": {
                "id": model_output.id,
                "input_text": model_output.input_text,
                "output_text": model_output.output_text,
                "doctor_remark": model_output.doctor_remark,
                "doctor_comment": model_output.doctor_comment,
                "doctor_note": model_output.doctor_note,
                "patient_mobile_number": model_output.patient_mobile_number,
                "created_at": model_output.created_at,
                "updated_at": model_output.updated_at,
            },
            "sensor_data": {
                "id": sensor_data.id,
                "doctor_id": sensor_data.doctor_id,
                "patient_mobile_number": sensor_data.patient_mobile_number,
                "device_serial_number": sensor_data.device_serial_number,
                "co": sensor_data.co,
                "co2": sensor_data.co2,
                "o2": sensor_data.o2,
                "heart_rate": sensor_data.heart_rate,
                "spo2": sensor_data.spo2,
                "nh3": sensor_data.nh3,
                "created_at": sensor_data.created_at,
            }
        }

        return Response(response_data,status=status.HTTP_200_OK)


