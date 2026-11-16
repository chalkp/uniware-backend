"""Private photo processing and transactional file lifecycle."""

import logging
import warnings
from contextvars import ContextVar
from functools import wraps
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)
_uploads = ContextVar("photo_uploads", default=None)


def strip_jpeg_metadata(data):
    """Remove JPEG application/comment segments without recompressing pixels."""
    output = bytearray(data[:2])
    position = 2
    while position < len(data):
        start = position
        if data[position] != 255:
            raise ValueError("Invalid JPEG marker")
        while data[position] == 255:
            position += 1
        marker = data[position]
        position += 1
        if marker in (0xDA, 0xD9):
            output.extend(data[start:])
            return bytes(output)
        length = int.from_bytes(data[position : position + 2], "big")
        if length < 2 or position + length > len(data):
            raise ValueError("Invalid JPEG segment")
        position += length
        if not (0xE1 <= marker <= 0xEF or marker == 0xFE):
            output.extend(data[start:position])
    raise ValueError("Incomplete JPEG")


def delete_files(names):
    for name in names:
        if name:
            try:
                default_storage.delete(name)
            except OSError:
                logger.exception("Photo cleanup failed for %s", name)


def photo_atomic(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        names = []
        token = _uploads.set(names)
        try:
            with transaction.atomic():
                return function(*args, **kwargs)
        except Exception:
            delete_files(names)
            raise
        finally:
            _uploads.reset(token)

    return wrapped


def process_photo(upload):
    if upload.size > settings.PHOTO_UPLOAD_MAX_BYTES:
        raise serializers.ValidationError("Photo must be at most 20 MiB.")
    extension = Path(upload.name).suffix
    formats = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
    expected = formats.get(extension.lower())
    if expected is None:
        raise serializers.ValidationError("Choose a JPEG, PNG, or WebP photo.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as source:
                if source.format != expected or getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Unsupported image content")
                if source.width * source.height > settings.PHOTO_MAX_PIXELS:
                    raise ValueError("Image dimensions exceed the safety limit")
                source.load()
                orientation = source.getexif().get(274, 1)
                oriented = ImageOps.exif_transpose(source)
                alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                clean = Image.new("RGBA" if alpha else "RGB", oriented.size)
                clean.paste(oriented.convert(clean.mode))
                original = BytesIO()
                options = {"quality": 100, "subsampling": 0} if expected == "JPEG" else {}
                if expected == "WEBP":
                    options = {"lossless": True}
                clean.save(original, format=expected, **options)
                original_bytes = original.getvalue()
                if expected == "JPEG" and orientation == 1:
                    upload.seek(0)
                    original_bytes = strip_jpeg_metadata(upload.read())
                clean.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
                for quality in (80, 65, 50, 35):
                    preview = BytesIO()
                    clean.save(preview, format="WEBP", quality=quality, method=3)
                    if preview.tell() < 1024 * 1024:
                        return original_bytes, preview.getvalue(), extension
                    clean.thumbnail((max(1, clean.width * 3 // 4), max(1, clean.height * 3 // 4)))
                raise ValueError("Unable to produce a preview below 1 MiB")
    except (
        UnidentifiedImageError,
        OSError,
        IndexError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise serializers.ValidationError(
            "Photo is invalid, too large in dimensions, or cannot be processed."
        ) from exc


def save_photo(instance, processed, slot=1):
    original, preview, extension = processed
    prefix = "photo" if slot == 1 else f"photo_{slot}"
    original_field, preview_field = f"{prefix}_original", f"{prefix}_preview"
    old = [getattr(instance, original_field), getattr(instance, preview_field)]
    names = _uploads.get()
    if names is None:
        raise RuntimeError("Photo writes require photo_atomic")
    key = f"photos/{uuid4().hex}"
    try:
        original_name = default_storage.save(f"{key}/original{extension}", ContentFile(original))
        names.append(original_name)
        preview_name = default_storage.save(f"{key}/preview.webp", ContentFile(preview))
        names.append(preview_name)
        setattr(instance, original_field, original_name)
        setattr(instance, preview_field, preview_name)
    except OSError as exc:
        raise APIException("Photo storage failed. Please retry or remove the attachment.") from exc
    instance.save(update_fields=[original_field, preview_field])
    transaction.on_commit(lambda: delete_files(old))


class PhotoSerializerMixin(serializers.Serializer):
    photo = serializers.FileField(write_only=True, required=False)
    photo_preview_url = serializers.SerializerMethodField()
    photo_original_url = serializers.SerializerMethodField()

    def validate_photo(self, value):
        return process_photo(value)

    def photo_url(self, obj, variant):
        if not getattr(obj, f"photo_{variant}"):
            return None
        resource = "equipment" if obj._meta.model_name == "equipment" else "returns"
        return f"/api/photos/{resource}/{obj.pk}/{variant}"

    def get_photo_preview_url(self, obj):
        return self.photo_url(obj, "preview")

    def get_photo_original_url(self, obj):
        return self.photo_url(obj, "original")

    def create(self, validated_data):
        photo = validated_data.pop("photo", None)
        instance = super().create(validated_data)
        if photo is not None:
            save_photo(instance, photo)
        return instance

    def update(self, instance, validated_data):
        photo = validated_data.pop("photo", None)
        instance = super().update(instance, validated_data)
        if photo is not None:
            save_photo(instance, photo)
        return instance
