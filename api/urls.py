from django.urls import path
from .views import GenerateGrokResponse, PatientView, StatusView, SinglePatientView

urlpatterns = [
    path("generate", GenerateGrokResponse.as_view(), name="Generate"),
    path("patient", PatientView.as_view(), name="Patient"),
    path("patient/<int:id>", SinglePatientView.as_view(), name="Patient"),
    path("status/<int:id>", StatusView.as_view(), name="Status"),
    # path("patient-detail", PatientDetailView.as_view(), name="Patient"),
]
