from rest_framework.exceptions import APIException
from rest_framework import permissions

class DeviceNotRegisteredException(APIException):
    status_code = 460
    default_detail = "Register device first."
    default_code = "device_not_registered"

class EmailVerificationException(APIException):
    status_code = 461
    default_detail = "Verify Email first."
    default_code = "email_not_verified"

class DeviceRegisteredPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.is_authenticated and not request.user.email_verified:
            raise EmailVerificationException()  # Raises exception with status code 461

        # Check if device_serial_number is an empty list or None
        if request.user.is_authenticated and not request.user.device_serial_numbers:
            raise DeviceNotRegisteredException()  # Raises exception with status code 460

        if request.user.is_authenticated and isinstance(request.user.device_serial_numbers, list) and len(request.user.device_serial_numbers) == 0:
            raise DeviceNotRegisteredException()  # Handles empty list case

        return True

