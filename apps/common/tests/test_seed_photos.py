from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from PIL import Image

from apps.equipment.models import Equipment

pytestmark = pytest.mark.django_db


def picture(path, color):
    image = Image.new("RGB", (20, 20), color)
    image.save(path)


def test_seed_imports_missing_slots_without_overwriting(settings, tmp_path):
    settings.BASE_DIR = tmp_path
    settings.MEDIA_ROOT = tmp_path / "media"
    directory = tmp_path / "seed_assets" / "equipment"
    directory.mkdir(parents=True)
    picture(directory / "UNIWARE-0001-1.jpg", "red")
    picture(directory / "UNIWARE-0001-3.png", "blue")
    call_command("seed", stdout=StringIO())
    item = Equipment.objects.get(asset_id="UNIWARE-0001")
    assert item.photo_original and not item.photo_2_original and item.photo_3_original
    assert (settings.MEDIA_ROOT / item.photo_original).is_file()
    assert (settings.MEDIA_ROOT / item.photo_3_preview).is_file()
    old = item.photo_original
    picture(directory / "UNIWARE-0001-1.jpg", "green")
    picture(directory / "UNIWARE-0001-2.webp", "green")
    call_command("seed", stdout=StringIO())
    item.refresh_from_db()
    assert item.photo_original == old
    assert item.photo_2_original.endswith(".webp")
    assert Equipment.objects.get(asset_id="UNIWARE-0002").photo_original == ""


def test_duplicate_slot_rolls_back_and_cleans_files(settings, tmp_path):
    settings.BASE_DIR = tmp_path
    settings.MEDIA_ROOT = tmp_path / "media"
    directory = tmp_path / "seed_assets" / "equipment"
    directory.mkdir(parents=True)
    picture(directory / "UNIWARE-0001-1.jpg", "red")
    picture(directory / "UNIWARE-0001-2.jpg", "red")
    picture(directory / "UNIWARE-0001-2.png", "red")
    with pytest.raises(CommandError, match="Multiple seed photos"):
        call_command("seed", stdout=StringIO())
    assert not Equipment.objects.exists()
    assert not [path for path in settings.MEDIA_ROOT.rglob("*") if path.is_file()]
