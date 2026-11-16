from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.common.photos import process_photo
from apps.equipment.factories import EquipmentFactory
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def upload(fmt="JPEG", size=(2200, 1200), suffix=".jpg"):
    image = Image.new("RGB", size, "orange")
    exif = Image.Exif()
    exif[315] = "Private photographer"
    stream = BytesIO()
    image.save(stream, format=fmt, exif=exif)
    return SimpleUploadedFile("photo" + suffix, stream.getvalue(), content_type="image/" + fmt.lower())


@pytest.fixture(autouse=True)
def private_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.mark.parametrize(("fmt", "suffix"), [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")])
def test_processing_strips_metadata_preserves_format_and_bounds_preview(fmt, suffix):
    original, preview, extension = process_photo(upload(fmt, suffix=suffix))
    assert extension == suffix
    with Image.open(BytesIO(original)) as image:
        assert image.format == fmt
        assert image.size == (2200, 1200)
        assert not image.getexif()
    with Image.open(BytesIO(preview)) as image:
        assert image.format == "WEBP"
        assert max(image.size) == 1920
        assert not image.getexif()
    assert len(preview) < 1024 * 1024


def test_equipment_upload_replace_and_protected_download(
    api_client, provider, borrower, private_media, django_capture_on_commit_callbacks
):
    equipment = EquipmentFactory(provider=provider)
    api_client.force_authenticate(provider)
    with django_capture_on_commit_callbacks(execute=True):
        response = api_client.patch(f"/api/equipment/{equipment.pk}", {"photo": upload()}, format="multipart")
    assert response.status_code == 200, response.data
    equipment.refresh_from_db()
    old = [equipment.photo_original, equipment.photo_preview]
    api_client.force_authenticate(borrower)
    for key in ("photo_preview_url", "photo_original_url"):
        result = api_client.get(response.data[key])
        assert result.status_code == 200
        assert b"".join(result.streaming_content)
        assert result["Cache-Control"] == "private, no-store"
    api_client.force_authenticate(provider)
    with django_capture_on_commit_callbacks(execute=True):
        replacement = api_client.patch(
            f"/api/equipment/{equipment.pk}", {"photo": upload()}, format="multipart"
        )
    assert replacement.status_code == 200
    assert all(not (private_media / name).exists() for name in old)
    api_client.force_authenticate(None)
    assert api_client.get(response.data["photo_original_url"]).status_code == 401


def test_invalid_equipment_photo_preserves_existing_files(api_client, provider, private_media):
    equipment = EquipmentFactory(provider=provider)
    api_client.force_authenticate(provider)
    url = f"/api/equipment/{equipment.pk}"
    assert api_client.patch(url, {"photo": upload()}, format="multipart").status_code == 200
    equipment.refresh_from_db()
    old = equipment.photo_original
    result = api_client.patch(
        url, {"photo": SimpleUploadedFile("bad.jpg", b"not an image")}, format="multipart"
    )
    assert result.status_code == 400
    equipment.refresh_from_db()
    assert equipment.photo_original == old
    assert (private_media / old).exists()


@pytest.mark.parametrize("actor", ["borrower", "other_provider"])
def test_only_owner_can_replace(api_client, provider, borrower, other_provider, actor):
    equipment = EquipmentFactory(provider=provider)
    api_client.force_authenticate({"borrower": borrower, "other_provider": other_provider}[actor])
    response = api_client.patch(f"/api/equipment/{equipment.pk}", {"photo": upload()}, format="multipart")
    assert response.status_code == (403 if actor == "borrower" else 404)


def loan(borrower, provider):
    equipment = EquipmentFactory(provider=provider, status="CHECKED_OUT")
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=equipment,
        pickup_date=date.today(),
        due_date=date.today(),
        purpose="Course project",
        status="CHECKED_OUT",
    )


def test_return_photo_is_private_and_cannot_be_overwritten(api_client, provider, borrower, other_provider):
    record = loan(borrower, provider)
    api_client.force_authenticate(provider)
    url = f"/api/provider/requests/{record.pk}/return"
    response = api_client.post(url, {"return_condition": "Good", "photo": upload()}, format="multipart")
    assert response.status_code == 200, response.data
    record.refresh_from_db()
    assert record.status == "RETURNED"
    photo_url = response.data["photo_original_url"]
    assert api_client.get(photo_url).status_code == 200
    assert (
        api_client.post(url, {"return_condition": "Good", "photo": upload()}, format="multipart").status_code
        == 409
    )
    for user in (borrower, other_provider):
        api_client.force_authenticate(user)
        assert api_client.get(photo_url).status_code == 404


def test_failed_return_upload_keeps_loan_active_and_allows_no_photo_retry(
    api_client, provider, borrower, private_media
):
    record = loan(borrower, provider)
    api_client.force_authenticate(provider)
    url = f"/api/provider/requests/{record.pk}/return"
    from django.core.files.storage import default_storage

    original_save = default_storage.save
    calls = []

    def fail_preview(name, content):
        calls.append(name)
        if len(calls) == 2:
            raise OSError("Disk full")
        return original_save(name, content)

    with patch.object(default_storage, "save", side_effect=fail_preview):
        result = api_client.post(url, {"return_condition": "Good", "photo": upload()}, format="multipart")
    assert result.status_code == 500
    record.refresh_from_db()
    record.equipment.refresh_from_db()
    assert record.status == record.equipment.status == "CHECKED_OUT"
    assert not record.photo_original
    assert record.returned_at is None
    assert not [path for path in private_media.rglob("*") if path.is_file()]
    assert api_client.post(url, {"return_condition": "Good"}, format="json").status_code == 200


def test_hidden_equipment_photo_is_hidden_and_missing_file_returns_404(api_client, provider, borrower):
    equipment = EquipmentFactory(provider=provider, status="ARCHIVED", photo_original="missing.jpg")
    url = f"/api/photos/equipment/{equipment.pk}/original"
    api_client.force_authenticate(borrower)
    assert api_client.get(url).status_code == 404
    api_client.force_authenticate(provider)
    assert api_client.get(url).status_code == 404
    assert api_client.get(url.replace("original", "unknown")).status_code == 404


def test_photo_limits_and_invalid_formats(settings):
    from rest_framework.exceptions import ValidationError

    settings.PHOTO_UPLOAD_MAX_BYTES = 1
    with pytest.raises(ValidationError, match="20 MiB"):
        process_photo(upload())
    settings.PHOTO_UPLOAD_MAX_BYTES = 20 * 1024 * 1024
    settings.PHOTO_MAX_PIXELS = 1
    with pytest.raises(ValidationError, match="invalid"):
        process_photo(upload())
    with pytest.raises(ValidationError, match="Choose"):
        process_photo(SimpleUploadedFile("bad.svg", b"<svg/>"))


def test_equipment_create_with_photo(api_client, provider):
    reference = EquipmentFactory(provider=provider)
    api_client.force_authenticate(provider)
    response = api_client.post(
        "/api/equipment",
        {
            "asset_id": "PHOTO-NEW",
            "name": "Camera",
            "category_id": str(reference.category_id),
            "location_id": str(reference.location_id),
            "photo": upload(),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.data
    assert response.data["photo_preview_url"]
    assert response.data["photo_original_url"]


def test_invalid_return_photo_can_be_removed_and_retried(api_client, provider, borrower):
    record = loan(borrower, provider)
    api_client.force_authenticate(provider)
    url = f"/api/provider/requests/{record.pk}/return"
    response = api_client.post(
        url,
        {
            "return_condition": "Good",
            "photo": SimpleUploadedFile("bad.jpg", b"broken"),
        },
        format="multipart",
    )
    assert response.status_code == 400
    record.refresh_from_db()
    assert record.status == "CHECKED_OUT"
    assert api_client.post(url, {"return_condition": "Good"}).status_code == 200


def test_orientation_is_applied_before_metadata_removal():
    image = Image.new("RGB", (60, 40), "orange")
    exif = Image.Exif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    original, preview, _ = process_photo(SimpleUploadedFile("rotated.jpeg", buffer.getvalue()))
    for data in (original, preview):
        with Image.open(BytesIO(data)) as result:
            assert result.size == (40, 60)
            assert not result.getexif()


def test_metadata_removal_preserves_unrotated_jpeg_pixels():
    file = upload(size=(60, 40))
    with Image.open(file) as source:
        pixels = source.tobytes()
    file.seek(0)
    original, _, _ = process_photo(file)
    with Image.open(BytesIO(original)) as result:
        assert result.tobytes() == pixels


def test_archived_equipment_cannot_replace_photo(api_client, provider, private_media):
    equipment = EquipmentFactory(provider=provider, status="ARCHIVED")
    api_client.force_authenticate(provider)
    result = api_client.patch(f"/api/equipment/{equipment.pk}", {"photo": upload()}, format="multipart")
    assert result.status_code == 409
    equipment.refresh_from_db()
    assert equipment.status == "ARCHIVED"
    assert equipment.photo_original == equipment.photo_preview == ""
    assert not [path for path in private_media.rglob("*") if path.is_file()]


def test_provider_handover_then_photo_return_preserves_audit(api_client, provider, borrower):
    record = loan(borrower, provider)
    record.status = "APPROVED"
    record.save(update_fields=["status"])
    record.equipment.status = "AVAILABLE"
    record.equipment.save(update_fields=["status"])
    api_client.force_authenticate(provider)
    checkout = api_client.post(f"/api/provider/requests/{record.pk}/checkout", {}, format="json")
    assert checkout.status_code == 200
    audit = checkout.data["checkout_record"]
    assert audit["handover_person"]["id"] == str(provider.pk)
    returned = api_client.post(
        f"/api/provider/requests/{record.pk}/return",
        {"return_condition": "Good", "photo": upload()},
        format="multipart",
    )
    assert returned.status_code == 200
    assert returned.data["checkout_record"] == audit
    assert api_client.get(returned.data["photo_original_url"]).status_code == 200


def test_equipment_three_photos_replace_and_limit(api_client, provider, borrower, other_provider):
    item = EquipmentFactory(provider=provider)
    api_client.force_authenticate(provider)
    url = f"/api/equipment/{item.pk}"
    result = api_client.patch(
        url,
        {"photo": upload(size=(30, 30)), "photo_2": upload(size=(30, 30)), "photo_3": upload(size=(30, 30))},
        format="multipart",
    )
    assert result.status_code == 200, result.data
    photos = result.data["photos"]
    assert [photo["slot"] for photo in photos] == [1, 2, 3]
    assert result.data["photo_original_url"] == photos[0]["original_url"]
    item.refresh_from_db()
    original = item.photo_2_original
    api_client.force_authenticate(borrower)
    for photo in photos:
        assert api_client.get(photo["preview_url"]).status_code == 200
        assert api_client.get(photo["original_url"]).status_code == 200
    api_client.force_authenticate(other_provider)
    assert api_client.patch(url, {"photo_2": upload(size=(30, 30))}, format="multipart").status_code == 404
    api_client.force_authenticate(provider)
    assert api_client.patch(url, {"photo_4": upload(size=(30, 30))}, format="multipart").status_code == 400
    result = api_client.patch(url, {"photo_2": upload(size=(30, 30))}, format="multipart")
    assert result.status_code == 200
    item.refresh_from_db()
    assert item.photo_2_original != original
    assert len(result.data["photos"]) == 3


def test_owner_can_delete_a_single_photo_slot(api_client, provider, borrower):
    item = EquipmentFactory(provider=provider)
    api_client.force_authenticate(provider)
    url = f"/api/equipment/{item.pk}"
    added = api_client.patch(
        url, {"photo": upload(size=(30, 30)), "photo_2": upload(size=(30, 30))}, format="multipart"
    )
    assert added.status_code == 200
    photo_url = added.data["photos"][0]["original_url"]
    api_client.force_authenticate(borrower)
    assert api_client.patch(url, {"remove_photos": [1]}, format="json").status_code == 403
    api_client.force_authenticate(provider)
    result = api_client.patch(url, {"remove_photos": ["1"]}, format="multipart")
    assert result.status_code == 200, result.data
    assert [photo["slot"] for photo in result.data["photos"]] == [2]
    assert api_client.get(photo_url).status_code == 404
