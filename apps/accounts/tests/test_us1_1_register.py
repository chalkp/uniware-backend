import pytest

from apps.accounts.models import ConsentRecord, User

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        "email": "newuser@chula.ac.th",
        "password": "Str0ngPassw0rd!",
        "first_name": "Somchai",
        "last_name": "Srisawat",
        "data_storage_consent": True,
    }
    payload.update(overrides)
    return payload


def test_us1_1_accepts_valid_domain_password_and_name(api_client):
    response = api_client.post(
        "/api/auth/register",
        _payload(),
        format="json",
        HTTP_USER_AGENT="pytest-agent/1.0",
        HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.1",
    )

    assert response.status_code == 201
    user = User.objects.get(email="newuser@chula.ac.th")
    assert user.check_password("Str0ngPassw0rd!")
    assert user.is_borrower is True

    record = ConsentRecord.objects.get(user=user)
    assert record.consent_version == ConsentRecord.CURRENT_VERSION
    assert record.consent_text_hash == ConsentRecord.current_text_hash()
    assert record.granted_at is not None
    assert record.ip_address == "203.0.113.10"
    assert record.user_agent == "pytest-agent/1.0"


def test_us1_1_requires_data_storage_consent(api_client):
    payload = _payload()
    del payload["data_storage_consent"]

    response = api_client.post("/api/auth/register", payload, format="json")

    assert response.status_code == 400
    assert "data_storage_consent" in response.data["error"]["details"]
    assert not User.objects.filter(email="newuser@chula.ac.th").exists()
    assert ConsentRecord.objects.count() == 0


def test_us1_1_rejects_declined_data_storage_consent(api_client):
    response = api_client.post("/api/auth/register", _payload(data_storage_consent=False), format="json")

    assert response.status_code == 400
    assert "data_storage_consent" in response.data["error"]["details"]
    assert not User.objects.filter(email="newuser@chula.ac.th").exists()
    assert ConsentRecord.objects.count() == 0


def test_us1_5_authenticated_user_reads_only_own_consent_records(api_client, borrower):
    ConsentRecord.objects.create(
        user=borrower,
        consent_version=ConsentRecord.CURRENT_VERSION,
        consent_text_hash=ConsentRecord.current_text_hash(),
    )
    api_client.post("/api/auth/register", _payload(), format="json")
    user = User.objects.get(email="newuser@chula.ac.th")
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/auth/consent")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["consent_version"] == ConsentRecord.CURRENT_VERSION
    assert response.data[0]["consent_text_hash"] == ConsentRecord.current_text_hash()
    assert "granted_at" in response.data[0]


def test_us1_5_authenticated_user_can_submit_new_consent_record(api_client, borrower):
    api_client.force_authenticate(user=borrower)

    bad_response = api_client.post("/api/auth/consent", {"data_storage_consent": False}, format="json")
    assert bad_response.status_code == 400

    ok_response = api_client.post("/api/auth/consent", {"data_storage_consent": True}, format="json")
    assert ok_response.status_code == 201
    assert ConsentRecord.objects.filter(user=borrower).count() == 1


def test_us1_5_rejects_unauthenticated_consent_access(api_client):
    get_response = api_client.get("/api/auth/consent")
    post_response = api_client.post("/api/auth/consent", {"data_storage_consent": True}, format="json")

    assert get_response.status_code in (401, 403)
    assert post_response.status_code in (401, 403)


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
