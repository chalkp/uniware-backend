import factory
from factory.django import DjangoModelFactory

from .models import User

DEFAULT_PASSWORD = "Str0ngPassw0rd!"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@chula.ac.th")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_borrower = True
    is_provider = False
    is_admin = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):  # noqa: FBT002
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class ProviderFactory(UserFactory):
    is_provider = True


class BorrowerProviderFactory(UserFactory):
    """A user with both capabilities at once (see docs/DECISIONS.md)."""

    is_provider = True
    is_borrower = True


class AdminFactory(UserFactory):
    is_admin = True
    is_staff = True
    is_superuser = True
