from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication as _SessionAuthentication


class SessionAuthentication(_SessionAuthentication):
    def authenticate_header(self, request):
        return "Session"


class SessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.common.authentication.SessionAuthentication"
    name = "SessionAuthentication"

    def get_security_definition(self, auto_schema):
        return {"type": "apiKey", "in": "cookie", "name": "sessionid"}
