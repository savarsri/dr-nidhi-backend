from django.urls import path
from .views import (GenerateJiviResponse, PatientView, StatusView,
                    SinglePatientView, LoginView, UserRegistrationUpdateAPIView, 
                    Check, DoctorRemark, RegisterDeviceView, LLMOutputCheck, DeviceLoginView,
                    TestEmail, VerifyEmailView, ResendVerificationEmailView, AdminDashboard,
                    DoctorView, RequestOTPView, VerifyOTPView, PromptStatusView)

urlpatterns = [
    path("check", Check.as_view(), name="Check"),
    path("generate", GenerateJiviResponse.as_view(), name="Generate"),
    path("patient", PatientView.as_view(), name="Patient"),
    path("patient/<int:id>", SinglePatientView.as_view(), name="Patient"),
    path("status/<int:id>", StatusView.as_view(), name="Status"),
    path("login", LoginView.as_view(), name="Login"),
    path("user", UserRegistrationUpdateAPIView.as_view(), name="Register/Update User"),
    path("doctor-remark", DoctorRemark.as_view(), name="Doctor Remark"),
    path("device-register", RegisterDeviceView.as_view(), name="Device Register"),
    path("device-login", DeviceLoginView.as_view(), name="Device Login"),
    path("output/<int:id>", LLMOutputCheck.as_view(), name="Output Check"),
    path("testemail", TestEmail.as_view(), name="Email Test"),
    path('verify-email/<uidb64>/<token>', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification-email', ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    path('admin-dashboard', AdminDashboard.as_view(), name='admin-dashboard'),
    path('doctor', DoctorView.as_view(), name='Doctor List'),
    path('request-otp', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp', VerifyOTPView.as_view(), name='verify-otp'),
    path('prompt-status', PromptStatusView.as_view(), name='prompt_status'),
    # path("patient-detail", PatientDetailView.as_view(), name="Patient"),
]
