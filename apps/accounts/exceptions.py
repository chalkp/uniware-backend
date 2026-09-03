from rest_framework import status

from apps.common.exceptions import DomainError


class InvalidCredentials(DomainError):
    """US1-2"""

    default_code = "INVALID_CREDENTIALS"
    status_code = status.HTTP_401_UNAUTHORIZED
