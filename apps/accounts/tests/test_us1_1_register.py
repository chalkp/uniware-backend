import pytest

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        "email": "newuser@chula.ac.th",
        "password": "Str0ngPassw0rd!",
        "first_name": "Somchai",
        "last_name": "Srisawat",
    }
    payload.update(overrides)
    return payload


def test_us1_1_accepts_valid_domain_password_and_name(api_client):
    response = api_client.post("/api/auth/register", _payload(), format="json")

    assert response.status_code == 201
    user = User.objects.get(email="newuser@chula.ac.th")
    assert user.check_password("Str0ngPassw0rd!")
    assert user.is_borrower is True


def test_us1_1_accepts_subdomain_of_approved_domain(api_client):
    response = api_client.post("/api/auth/register", _payload(email="student@eng.chula.ac.th"), format="json")

    assert response.status_code == 201


def test_us1_1_rejects_unapproved_email_domain(api_client):
    response = api_client.post("/api/auth/register", _payload(email="user@gmail.com"), format="json")

    assert response.status_code == 400
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert not User.objects.filter(email="user@gmail.com").exists()


def test_us1_1_rejects_insecure_password(api_client):
    response = api_client.post(
        "/api/auth/register", _payload(email="weak@chula.ac.th", password="12345678"), format="json"
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="weak@chula.ac.th").exists()


def test_us1_1_rejects_invalid_name(api_client):
    response = api_client.post(
        "/api/auth/register", _payload(email="badname@chula.ac.th", first_name="Us3r123"), format="json"
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="badname@chula.ac.th").exists()


def test_us1_1_rejects_duplicate_email(api_client, borrower):
    response = api_client.post("/api/auth/register", _payload(email=borrower.email), format="json")

    assert response.status_code == 400
    assert User.objects.filter(email=borrower.email).count() == 1
