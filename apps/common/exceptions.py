from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler

_DEFAULT_CODES = {
    status.HTTP_400_BAD_REQUEST: "VALIDATION_ERROR",
    status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_REQUIRED",
    status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_429_TOO_MANY_REQUESTS: "THROTTLED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "SERVER_ERROR",
}


class DomainError(drf_exceptions.APIException):

    status_code = status.HTTP_409_CONFLICT
    default_code = "CONFLICT"

    def __init__(self, message, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        self.code = code or self.default_code
        super().__init__(message)


class InvalidStateTransition(DomainError):
    default_code = "INVALID_STATE_TRANSITION"


class BookingConflict(DomainError):
    default_code = "BOOKING_CONFLICT"


def uniware_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "code", None) or _DEFAULT_CODES.get(response.status_code, "ERROR")
    message = _extract_message(response.data)

    details = None
    if isinstance(response.data, dict) and set(response.data.keys()) != {"detail"}:
        details = response.data
    elif isinstance(response.data, list):
        details = response.data

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response


def _extract_message(data):
    if isinstance(data, dict):
        if isinstance(data.get("detail"), str):
            return data["detail"]
        for value in data.values():
            message = _extract_message(value)
            if message:
                return message
        return "Request failed."
    if isinstance(data, list):
        for item in data:
            message = _extract_message(item)
            if message:
                return message
        return "Request failed."
    return str(data)
