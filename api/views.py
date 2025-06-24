import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.exceptions import ValidationError
from django.db.utils import DatabaseError

from datetime import datetime, timedelta

from django.db.models import OuterRef, Subquery, Exists, Q, Count
from django.utils.timezone import make_aware
from django.shortcuts import get_object_or_404

from .pagination import StandardResultsSetPagination

from .models import PatientDeviceData, PatientData, LLMOutput, CustomUser, OneTimePassword
from .serializer import (PatientDeviceDataSerializer, PatientDataSerializer, UserRegistrationSerializer, 
                         UserUpdateSerializer, LLMOutputSerializer, EmailSerializer, OTPVerificationSerializer)

from .prompt_jivi import (generate_actions_prompt, generate_alerts_prompt, generate_analysis_prompt, 
                         generate_base_prompt, generate_insights_prompt, generate_medication_prompt,
                         generate_summary_prompt, generate_diagnosis_prompt, generate_system_prompt,
                         grok_image_prompt, generate_initial_prompt, generate_organ_prompt, generate_table_prompt)

from .generate_jivi import send_to_jivi, send_to_grok

from .permissions import DeviceRegisteredPermission

from .tasks import generate_prompt_in_background, PROMPT_IDS, redis_key, REDIS_CONN

from google.cloud import storage
from django.utils.timezone import now
from django.core.mail import send_mail
from django.conf import settings

from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags

User = get_user_model()

class CustomLoginView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "Email and password required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=username, password=password)

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail": "User account is disabled."}, status=status.HTTP_403_FORBIDDEN)

        # READY FOR 2FA LATER HERE
        # if user.two_factor_enabled:
        #     send_otp_to_user(user)
        #     return Response({"detail": "OTP sent", "2fa_required": True}, status=202)

        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": getattr(user, "full_name", ""),
                "role": getattr(user, "role", ""),
            },
        }, status=status.HTTP_200_OK)

class GenerateJiviResponse(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    FILE_CATEGORIES = ['mri', 'ct_scan', 'xray', 'other']

    def post(self, request):
        try:
            user = request.user
            sensor_data_id = request.data['id']
            patientName = request.data['name']
            phoneNumber = request.data['phone']
            age = request.data['age']
            gender = request.data['gender']
            symptoms = request.data['majorsymptoms']
            history = request.data['medicalHistory']
            notes = request.data['notes']

            if not patientName or not isinstance(patientName, str) or not patientName.strip():
                return Response({'error': 'Name is required and must be a valid string.'}, status=status.HTTP_400_BAD_REQUEST)

            if not phoneNumber or not re.fullmatch(r'\d{10}', str(phoneNumber)):
                return Response({'error': 'Phone number must be exactly 10 digits.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                age = int(age)
                if age <= 0 or age > 150:
                    return Response({'error': 'Age must be between 1 and 150.'}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, TypeError):
                return Response({'error': 'Age must be a valid integer.'}, status=status.HTTP_400_BAD_REQUEST)


            # Create or get patient
            patient, created = PatientData.objects.get_or_create(
                patient_mobile_number=phoneNumber,
                defaults={'name': patientName, 'age': age, 'gender': gender}
            )

            sensor_data = PatientDeviceData.objects.filter(
                id=sensor_data_id,
                device_serial_number__in=user.device_serial_numbers
            ).first()
            if not sensor_data:
                return Response({"message": "Sensor Data Not Found"}, status=status.HTTP_404_NOT_FOUND)
            
            patientDeviceData = PatientDeviceDataSerializer(sensor_data)

            # File Upload Handling
            uploaded_files = {}
            client = storage.Client(credentials=settings.GS_CREDENTIALS)
            bucket = client.bucket(settings.GS_BUCKET_NAME)

            for category in self.FILE_CATEGORIES:
                file_obj = request.FILES.get(category)
                if file_obj:
                    # Rename file using sensor_id, phone number, timestamp, and category
                    timestamp = now().strftime("%Y%m%d%H%M%S")
                    file_extension = file_obj.name.split('.')[-1]
                    new_file_name = f"{sensor_data_id}_{phoneNumber}_{timestamp}_{category}.{file_extension}"

                    # Upload to GCP
                    blob = bucket.blob(f"uploads/{new_file_name}")
                    blob.upload_from_file(file_obj, content_type=file_obj.content_type)
                    signed_url = blob.generate_signed_url(expiration=timedelta(hours=72))  # Expires in 72 hours

                    uploaded_files[category] = signed_url

            # Check if any files were uploaded; if not, set output_text_10 accordingly
            output_text_10 = None
            if not uploaded_files:
                output_text_10 = "No files were uploaded"

            patient_data = {
                "patientName": patientName,
                "age": age,
                "gender": gender,
                "symptoms": symptoms,
                "medicalHistory": history,
                "notes": notes,
            }

            system_prompt = generate_system_prompt()
            base_prompt = generate_base_prompt(patient_data, patientDeviceData.data)
            user_prompt = generate_initial_prompt(base_prompt)
            table_prompt = generate_table_prompt(base_prompt)
            jivi_response = send_to_jivi(system_prompt, user_prompt)
            jivi_response_table = send_to_jivi(system_prompt, table_prompt)

            # Store LLM output and uploaded file URLs
            model_output = LLMOutput.objects.create(
                output_text_1=jivi_response,
                output_text_10=output_text_10,
                output_text_11=jivi_response_table,
                sensor_data=sensor_data,
                patient_mobile_number=phoneNumber,
                symptoms=symptoms,
                history=history,
                notes=notes,
                medication_type=user.medication,
                file_urls=uploaded_files
            )

            for prompt_id in PROMPT_IDS:
                # Mark as pending in redis
                REDIS_CONN.setex(redis_key(model_output.id, prompt_id), 300, "pending")  # expire in 15 min
                generate_prompt_in_background.delay(model_output.id, prompt_id)

            return Response({"model_output_id": model_output.id}, status=status.HTTP_200_OK)

        except RuntimeError as e:
            return Response({"message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            print(e)
            return Response({"message": f"Error Occurred. Error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
    def put(self, request):
        try:
            user = request.user
            output_id = request.data.get('output_id')
            prompt_id = request.data.get('prompt_id')
            reload = request.data.get('reload', False)

            if not prompt_id:
                return Response({"message": "prompt_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Optionally ensure prompt_id is an integer
            try:
                prompt_id = int(prompt_id)
            except ValueError:
                return Response({"message": "Invalid prompt_id"}, status=status.HTTP_400_BAD_REQUEST)

            status_val = REDIS_CONN.get(redis_key(output_id, prompt_id))
            if status_val:
                status_decoded = status_val.decode()
                if status_decoded in ("pending", "processing"):
                    return Response({
                        "status": status_decoded,
                        "message": "Output is being generated. Please try again later.",
                    }, status=status.HTTP_202_ACCEPTED)

            model_output = LLMOutput.objects.get(id=output_id)

            check_updated_text = getattr(model_output, f"output_text_{prompt_id}", None)

            if not reload and check_updated_text is not None and str(check_updated_text).strip() != "":
                serializer = LLMOutputSerializer(model_output)
                return Response({
                    "message": "Prompt output updated successfully",
                    "model_output_id": model_output.id,
                    "updatedText": check_updated_text,
                    "data": serializer.data,
                }, status=status.HTTP_200_OK)

            sensor_data = model_output.sensor_data

            if sensor_data.device_serial_number not in user.device_serial_numbers:
                  return Response({"message": "Data Does Not Match Your Device"}, status=status.HTTP_403_FORBIDDEN)
            
            patient_device_data = PatientDeviceDataSerializer(sensor_data).data

            patient = PatientData.objects.get(patient_mobile_number=model_output.patient_mobile_number)

            patient_data = {
                "patientName": patient.name,
                "age": patient.age,
                "gender": patient.gender,
                "symptoms": model_output.symptoms,
                "medicalHistory": model_output.history,
            }
            
            system_prompt = generate_system_prompt()
            base_prompt = generate_base_prompt(patient_data, patient_device_data)

            # Running different prompts and updating different output_text_n fields based on prompt_id
            if prompt_id == 1:
                model_output.output_text_1 = send_to_jivi(system_prompt, generate_initial_prompt(base_prompt))
            elif prompt_id == 2:
                model_output.output_text_2 = send_to_jivi(system_prompt, generate_diagnosis_prompt(base_prompt))
            elif prompt_id == 3:
                model_output.output_text_3 = send_to_jivi(system_prompt, generate_organ_prompt(base_prompt))
            elif prompt_id == 4:
                model_output.output_text_4 = send_to_jivi(system_prompt, generate_summary_prompt(base_prompt))
            elif prompt_id == 5:
                model_output.output_text_5 = send_to_jivi(system_prompt, generate_analysis_prompt(base_prompt))
            elif prompt_id == 6:
                model_output.output_text_6 = send_to_jivi(system_prompt, generate_alerts_prompt(base_prompt))
            elif prompt_id == 7:
                model_output.output_text_7 = send_to_jivi(system_prompt, generate_actions_prompt(base_prompt))
            elif prompt_id == 8:
                if model_output.medication_type:
                    model_output.output_text_8 = send_to_jivi(system_prompt, generate_medication_prompt(base_prompt, model_output.medication_type))
            elif prompt_id == 9:
                model_output.output_text_9 = send_to_jivi(system_prompt, generate_insights_prompt(base_prompt))
            elif prompt_id == 10:
                if not model_output.file_urls:
                    model_output.output_text_10 = "No files were uploaded"
                else:
                    model_output.output_text_10 = send_to_grok(grok_image_prompt(base_prompt), model_output.file_urls)
            else:
                return Response({"message": "Invalid prompt_id"}, status=status.HTTP_400_BAD_REQUEST)
            
            model_output.save()

            serializer = LLMOutputSerializer(model_output)

            # Dynamically get the updated text field.
            updated_text = getattr(model_output, f"output_text_{prompt_id}", None)

            return Response({
                "message": "Prompt output updated successfully",
                "model_output_id": model_output.id,
                "updatedText": updated_text,
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        except LLMOutput.DoesNotExist:
            return Response({"message": "Invalid prompt_id"}, status=status.HTTP_404_NOT_FOUND)
        
        except RuntimeError as e:
            return Response({"message": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
        except Exception as e:
            print(e)
            return Response({"message": "Error Occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SinglePatientView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    def get(self, request, id):
        patient = get_object_or_404(PatientData, patient_mobile_number=id)
        serializer = PatientDataSerializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)
   
class PatientView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    def get(self, request):
        try:
            # Extract query parameters
            user = request.user
            date_filter = request.GET.get("date_filter")  # e.g., "today", "yesterday", "last_week", "last_month", "old"
            search = request.GET.get("search")  # Search text for patient_mobile_number or patient_name

            # Define time boundaries
            today = make_aware(datetime.now())
            yesterday = today - timedelta(days=1)
            last_week = today - timedelta(days=7)
            last_month = today - timedelta(days=30)

            filter_conditions = Q(device_serial_number__in=user.device_serial_numbers, doctor_id=user.id )
            if date_filter == "today":
                filter_conditions &= Q(created_at__date=today.date())
            elif date_filter == "yesterday":
                filter_conditions &= Q(created_at__date=yesterday.date())
            elif date_filter == "last_week":
                filter_conditions &= Q(created_at__gte=last_week)
            elif date_filter == "last_month":
                filter_conditions &= Q(created_at__gte=last_month)
            elif date_filter == "old":
                # Records older than last month
                filter_conditions &= Q(created_at__lt=last_month)

            # Apply search filter if provided.
            # First, filter on patient_mobile_number field, and also search patient names via PatientData.
            if search:
                filter_conditions &= (
                    Q(patient_mobile_number__icontains=search) |
                    Q(patient_mobile_number__in=PatientData.objects.filter(name__icontains=search).values("patient_mobile_number"))
                )

            # Build a subquery to get the latest created_at for each patient (by mobile number)
            latest_records = PatientDeviceData.objects.filter(
                device_serial_number__in = user.device_serial_numbers,
                patient_mobile_number=OuterRef("patient_mobile_number")
            ).order_by("-created_at")

            # Filter for unique latest records and apply our filter conditions
            unique_latest_records = PatientDeviceData.objects.filter(
                created_at=Subquery(latest_records.values("created_at")[:1])
            ).filter(filter_conditions)

            # Prepare subqueries for model output information
            model_output_exists = LLMOutput.objects.filter(
                sensor_data_id=OuterRef("id")
            )
            model_output_id = LLMOutput.objects.filter(
                sensor_data_id=OuterRef("id")
            ).values("id").order_by("-created_at")[:1]

            # Annotate the queryset with additional fields (patient details and model info)
            queryset = unique_latest_records.annotate(
                patient_name=Subquery(
                    PatientData.objects.filter(
                        patient_mobile_number=OuterRef("patient_mobile_number")
                    ).values("name")[:1]
                ),
                patient_age=Subquery(
                    PatientData.objects.filter(
                        patient_mobile_number=OuterRef("patient_mobile_number")
                    ).values("age")[:1]
                ),
                patient_gender=Subquery(
                    PatientData.objects.filter(
                        patient_mobile_number=OuterRef("patient_mobile_number")
                    ).values("gender")[:1]
                ),
                model_generated=Exists(model_output_exists),
                model_output_id=Subquery(model_output_id),
            ).values(
                "id",
                "doctor_id",
                "patient_mobile_number",
                "device_serial_number",
                "co",
                "co2",
                "o2",
                "heart_rate",
                "spo2",
                "nh3",
                "created_at",
                "patient_name",
                "patient_age",
                "patient_gender",
                "model_generated",
                "model_output_id",
            ).order_by("-created_at")

            # Set up pagination
            paginator = StandardResultsSetPagination()
            paginated_queryset = paginator.paginate_queryset(queryset, request)

            # Serialize the paginated data
            serializer = PatientDeviceDataSerializer(paginated_queryset, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            # Optionally log the error here.
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    def get(self, request, id):
        user = request.user

        model_output = get_object_or_404(LLMOutput, id=id)

        if model_output.sensor_data.device_serial_number not in user.device_serial_numbers:
            return Response({"message": "Data Does Not Match Your Device"}, status=status.HTTP_403_FORBIDDEN)

        patient = PatientData.objects.get(patient_mobile_number=model_output.patient_mobile_number)
        
        previous_visits = LLMOutput.objects.filter(
            patient_mobile_number=model_output.patient_mobile_number
        ).exclude(id=id).values("id", "doctor_remark", "created_at").order_by("-created_at")

        visits_serializer = LLMOutputSerializer(previous_visits, many=True, fields=["id", "doctor_remark","created_at"])

        serializer = PatientDataSerializer(patient)

        sensor_data = model_output.sensor_data

        response_data = {
            "model_output": {
                "id": model_output.id,
                "symptoms" : model_output.symptoms,
                "history" : model_output.history,
                "output_text_1": model_output.output_text_1,
                "output_text_2": model_output.output_text_2,
                "output_text_3": model_output.output_text_3,
                "output_text_4": model_output.output_text_4,
                "output_text_5": model_output.output_text_5,
                "output_text_6": model_output.output_text_6,
                "output_text_7": model_output.output_text_7,
                "output_text_8": model_output.output_text_8,
                "output_text_9": model_output.output_text_9,
                "output_text_10": model_output.output_text_10,
                "output_text_11": model_output.output_text_11,
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
                "rq": sensor_data.rq,
                "hydrogen": sensor_data.hydrogen,
                "formaldehyde": sensor_data.formaldehyde,
                "created_at": sensor_data.created_at,
            },
            "patient_data" : serializer.data,
            "previous_visits" : visits_serializer.data
        }

        return Response(response_data,status=status.HTTP_200_OK)

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        today = make_aware(datetime.now())
        first_day_of_month = today.replace(day=1)

        patient_count = PatientData.objects.count()

        new_patients_this_month = PatientData.objects.filter(
            created_at__gte=first_day_of_month
        ).count()

        return Response(
            {
                "totalPatients": patient_count,
                "newPatientsThisMonth": new_patients_this_month,
            },
            status=status.HTTP_200_OK
        )

class UserRegistrationUpdateAPIView(APIView):
    """
    API endpoint for user registration (POST) and update (PUT).
    
    POST:
      - Registers a new user.
      - Does not require authentication.
    
    PUT:
      - Updates the currently authenticated user's information.
      - Requires authentication.
    """
    def get_permissions(self):
        # For PUT requests, require the user to be authenticated.
        if self.request.method.upper() == 'PUT':
            return [IsAuthenticated()]
        return []

    def post(self, request, *args, **kwargs):
        # Registration: Use the registration serializer.
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Password is set using set_password in the serializer.
            send_verification_email(self, user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        # Update: Use the update serializer on the currently authenticated user.
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()  # Save updated user data.
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Check(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        print(user)
        return Response({"user":user.id}, status=status.HTTP_200_OK)

class DoctorRemark(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    def post(self, request):
        output_id = request.data.get('output_id')
        remark = request.data.get('remark')
        comment = request.data.get('comment')

        if not output_id:
            return Response({"message": "Output ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            model_output = LLMOutput.objects.get(id=output_id)
            model_output.doctor_remark = remark
            model_output.doctor_comment = comment
            model_output.save()
            return Response({"status":True}, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
       
class RegisterDeviceView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            username = request.data.get("username")
            password = request.data.get("password")
            device_serial_number = request.data.get("device_serial_number")

            if not username or not password or not device_serial_number:
                return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

            user = authenticate(username=username, password=password)
            if user is None:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            # Initialize or append to device_serial_number list
            if not user.device_serial_numbers:
                user.device_serial_numbers = [device_serial_number]
            elif device_serial_number not in user.device_serial_numbers:
                user.device_serial_numbers.append(device_serial_number)

            user.save()
            return Response({"message": "Device registered successfully"}, status=status.HTTP_200_OK)
        
        except ValidationError as e:
            return Response({"error": "Invalid data", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({"error": "Database error. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": "An unexpected error occurred", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeviceLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            username = request.data.get("username")
            password = request.data.get("password")

            if not username or not password:
                return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

            user = authenticate(username=username, password=password)
            if user is None:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            return Response({"doctor_id": user.id}, status=status.HTTP_200_OK)
        
        except ValidationError as e:
            return Response({"error": "Invalid data", "details": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except DatabaseError:
            return Response({"error": "Database error. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": "An unexpected error occurred", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LLMOutputCheck(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]
    
    def get(self, request, id):
        try:
            user = request.user
            output = get_object_or_404(LLMOutput, sensor_data=id)

            if not output:
                return Response({"message":"Output does not exists"}, status=status.HTTP_404_NOT_FOUND)
            
            if output.sensor_data.device_serial_number not in user.device_serial_numbers:
                return Response({"message": "Data Does Not Match Your Device"}, status=status.HTTP_403_FORBIDDEN)
            
            return Response({"message":"Output exists"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"message":"Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TestEmail(APIView):
    authentication_classes = []
    permission_classes = []
    def get(self, request):
        try:
            user = CustomUser.objects.get(id=1)
            send_verification_email(self, user)
            # send_mail(
            #     subject='Test Email',
            #     message='This is a test email from the API.',
            #     from_email=settings.EMAIL_HOST_USER,
            #     recipient_list=['vidit@gmail.com'],  # Change this to your test email
            #     fail_silently=False,
            # )
            return Response({"message": "Test email sent successfully."}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

def send_verification_email(self, user):
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"

    subject = "Verify your email address"
    html_content = render_to_string('verify_email.html', {
        'username': user.username,
        'verify_url': link,
    })
    plain_text_content = strip_tags(html_content)  # Fallback for email clients that don't support HTML

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()
       
class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save()
            return Response({"status": True, "message": "User Email Verified"}, status=status.HTTP_200_OK)
        else:
            return Response({"status": False, "message": "Invalid Token, Try Again"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResendVerificationEmailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user  # or identify from session/cookie/context
        if not user.email_verified:
            send_verification_email(user)  # Your email sending logic
            return Response({"message": "Verification email resent."}, status=200)
        return Response({"message": "User already verified."}, status=400)
    
class AdminDashboard(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_date_range(self, filter_by, today):
        if filter_by == "today":
            start = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end = today
        elif filter_by == "yesterday":
            yesterday = today - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
        elif filter_by == "last_week":
            start = today - timedelta(days=7)
            end = today
        elif filter_by == "last_month":
            start = today.replace(day=1) - timedelta(days=1)
            start = start.replace(day=1)
            end = today.replace(day=1) - timedelta(seconds=1)
        elif filter_by == "old":
            # Everything before the current month
            start = None
            end = today.replace(day=1) - timedelta(seconds=1)
        else:  # "All"
            start = None
            end = None
        return start, end

    def get(self, request):
        filter_by = request.GET.get("filter", "All")
        doctor_id = request.GET.get("doctor_id")

        today = make_aware(datetime.now())
        start, end = self.get_date_range(filter_by, today)

        # Filter PatientData
        patient_qs = PatientData.objects.all()
        if start and end:
            patient_qs = patient_qs.filter(created_at__range=(start, end))

        total_patients = PatientData.objects.count()
        filtered_patients = patient_qs.count()

        # Filter PatientDeviceData
        device_qs = PatientDeviceData.objects.all()
        if doctor_id:
            device_qs = device_qs.filter(doctor_id=doctor_id)
        if start and end:
            device_qs = device_qs.filter(created_at__range=(start, end))
        total_device_data = device_qs.count()

        # New Users
        user_qs = CustomUser.objects.filter(created_at__range=(start, end)) if start and end else CustomUser.objects.all()
        new_users = user_qs.count()

        # LLMOutput Ratings (filtered by related sensor_data.doctor)
        llm_qs = LLMOutput.objects.all()
        if doctor_id:
            llm_qs = llm_qs.filter(sensor_data__doctor_id=doctor_id)
        if start and end:
            llm_qs = llm_qs.filter(created_at__range=(start, end))

        remark_counts = llm_qs.values('doctor_remark').annotate(count=Count('id'))
        remark_map = {r['doctor_remark']: r['count'] for r in remark_counts}

        ratings = ["Excellent", "Good", "Average", "Poor", "Bad"]
        categorized_remarks = {label: remark_map.get(label, 0) for label in ratings}

        return Response(
            {
                "chartData": {
                    "patientCounts": {
                        "total": total_patients,
                        "filtered": filtered_patients
                    },
                    "deviceDataTotal": total_device_data,
                    "newUsers": new_users,
                    "llmRemarkCounts": categorized_remarks
                }
            },
            status=status.HTTP_200_OK
        )

class DoctorView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        doctors = CustomUser.objects.filter(role='doctor').values('id', 'full_name')
        return Response(list(doctors), status=status.HTTP_200_OK)

class RequestOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except Exception as e:
            return Response({"message": "User lookup failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not user.email_verified:
            return Response({"message": "Kindly verify your email first"}, status=461)
        
        otp_instance = OneTimePassword.generate_otp(user)

        send_otp_email(self, user, otp_instance.otp)

        return Response({"message": "OTP sent to email."}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        latest_otp = OneTimePassword.objects.filter(user=user, is_expired=False).order_by('-created_at').first()

        if not latest_otp:
            return Response({"message": "No active OTP found. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if latest_otp.has_expired():
            return Response({"message": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        if latest_otp.otp != otp:
            return Response({"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        latest_otp.is_expired = True
        latest_otp.save(update_fields=['is_expired'])

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "OTP verified successfully.",
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    
def send_otp_email(self, user, otp):
    subject = "One Time Password (OTP) for login"
    html_content = render_to_string('otp_login.html', {
        'username': user.username,
        'otp': otp,
    })
    plain_text_content = strip_tags(html_content)  # Fallback for email clients that don't support HTML

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

class PromptStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, DeviceRegisteredPermission]

    def get(self, request):
        output_id = request.GET.get("output_id")
        prompt_id = request.GET.get("prompt_id")
        if not output_id or not prompt_id:
            return Response({"status": "invalid"}, status=400)
        status_val = REDIS_CONN.get(redis_key(output_id, prompt_id))
        if status_val:
            return Response({"status": status_val.decode()})
        return Response({"status": "not_started"})