import re

from django.conf import settings
from django.core.exceptions import ValidationError

_DISALLOWED_NAME_CHARS = re.compile(r"[0-9`~!@#$%^&*()_+=\[\]{}|\\;:\"<>/?]")


def validate_university_email(email):
    """US1-1"""
    domain = email.rsplit("@", 1)[-1].lower()
    approved = settings.APPROVED_EMAIL_DOMAIN.lower()
    if domain != approved and not domain.endswith("." + approved):
        raise ValidationError(
            f"Email must be an @{approved} address (or a subdomain of it).",
            code="invalid_university_email",
        )


def validate_person_name(value):
    """US1-1"""
    value = (value or "").strip()
    if not (1 <= len(value) <= 150):
        raise ValidationError("Name must be between 1 and 150 characters.", code="invalid_name")
    if _DISALLOWED_NAME_CHARS.search(value):
        raise ValidationError("Name contains characters that are not allowed.", code="invalid_name")
