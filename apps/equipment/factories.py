import factory
from factory.django import DjangoModelFactory

from apps.accounts.factories import ProviderFactory

from .models import Category, Equipment, EquipmentStatus, Location


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Category {n}")


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Location {n}")


class EquipmentFactory(DjangoModelFactory):
    class Meta:
        model = Equipment

    asset_id = factory.Sequence(lambda n: f"ASSET-{n:05d}")
    name = factory.Faker("word")
    model = factory.Faker("word")
    description = factory.Faker("sentence")
    provider = factory.SubFactory(ProviderFactory)
    category = factory.SubFactory(CategoryFactory)
    location = factory.SubFactory(LocationFactory)
    status = EquipmentStatus.AVAILABLE
