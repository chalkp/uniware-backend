"""
Populate the database
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.equipment.models import Category, Equipment, EquipmentStatus, Location

CATEGORIES = [
    "Actuators & Motors",
    "Cameras & Imaging",
    "Computing & GPUs",
    "Hand Tools",
    "Lab Instruments",
    "VR / AR Hardware",
]

LOCATIONS = [
    "Engineering Building 1, Room 101",
    "Engineering Building 2, Room 214",
    "Robotics Lab, Basement",
    "Faculty of Science, Room 305",
]

DEMO_PASSWORD = "Str0ngPassw0rd!"

PROVIDERS = [
    ("provider1@chula.ac.th", "Ekapol", "Chuangsuwanich"),
    ("provider2@chula.ac.th", "Sukhum", "Sattaratnamai"),
]

BORROWERS = [
    ("borrower1@chula.ac.th", "Sorrawit", "Poomseetong"),
    ("borrower2@chula.ac.th", "Tee", "Hemjinda"),
    ("borrower3@chula.ac.th", "Pralod", "Charoenvanitchakorn"),
]

EQUIPMENT_NAMES = [
    "Cubemars Motor AK80-9",
    "Cubemars Motor AK70-10",
    "Meta Quest 3 VR Headset",
    "HTC Vive Pro 2",
    "NVIDIA Jetson Orin Nano",
    "NVIDIA RTX 5090 GPU Node",
    "Lanta Credits",
    "Intel RealSense D435 Camera",
    "GoPro Hero 12",
    "DJI Mini 4 Pro Drone",
    "Digital Oscilloscope Tektronix TBS2000",
    "Bench Power Supply Keysight E36313A",
    "Soldering Station Hakko FX-888D",
    "3D Printer Prusa MK4",
    "Laser Cutter Glowforge Pro",
    "Torque Wrench Set",
    "Multimeter Fluke 87V",
    "Function Generator Rigol DG1032Z",
    "Thermal Camera FLIR E8",
    "Servo Tester Kit",
    "LiPo Battery Charger iCharger 4010",
]


class Command(BaseCommand):
    help = (
        "Idempotent demo data for the current backend scope (accounts + equipment). "
        "Borrow-request/loan seeding is added once EPIC4 lands."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._get_or_create_user(
            "admin@chula.ac.th", "Admin", "User", is_admin=True, is_staff=True, is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS(f"admin: {admin.email}"))

        providers = [
            self._get_or_create_user(email, first, last, is_provider=True) for email, first, last in PROVIDERS
        ]
        for provider in providers:
            self.stdout.write(self.style.SUCCESS(f"provider: {provider.email}"))

        for email, first, last in BORROWERS:
            borrower = self._get_or_create_user(email, first, last, is_borrower=True)
            self.stdout.write(self.style.SUCCESS(f"borrower: {borrower.email}"))

        categories = [Category.objects.get_or_create(name=name)[0] for name in CATEGORIES]
        for category in categories:
            self.stdout.write(self.style.SUCCESS(f"category: {category.name}"))

        locations = [Location.objects.get_or_create(name=name)[0] for name in LOCATIONS]
        for location in locations:
            self.stdout.write(self.style.SUCCESS(f"location: {location.name}"))

        for index, name in enumerate(EQUIPMENT_NAMES):
            asset_id = f"UNIWARE-{index + 1:04d}"
            equipment, created = Equipment.objects.get_or_create(
                asset_id=asset_id,
                defaults={
                    "name": name,
                    "provider": providers[index % len(providers)],
                    "category": categories[index % len(categories)],
                    "location": locations[index % len(locations)],
                    "status": EquipmentStatus.AVAILABLE,
                },
            )
            action = "created" if created else "already present"
            self.stdout.write(f"equipment: {asset_id} ({name}) — {action}")

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    @staticmethod
    def _get_or_create_user(email, first_name, last_name, **flags):
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": first_name, "last_name": last_name, **flags},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
        return user
