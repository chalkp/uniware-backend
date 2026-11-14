from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication as _SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.models import AccountStatus


class SessionAuthentication(_SessionAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None and result[0].account_status != AccountStatus.ACTIVE:
            raise AuthenticationFailed("This account is suspended.")
        return result

    def authenticate_header(self, request):
        return "Session"


class SessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.common.authentication.SessionAuthentication"
    name = "SessionAuthentication"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
