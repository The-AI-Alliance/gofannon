"""Factory classes for generating test User data."""
import factory
from factory import Faker
from datetime import timezone


class UserFactory(factory.Factory):
    """Factory for creating test User instances."""

    class Meta:
        model = dict

    uid = Faker('uuid4')
    email = Faker('email')
    email_verified = True
    display_name = Faker('name')
    photo_url = Faker('image_url')
    created_at = Faker('iso8601', tzinfo=timezone.utc)
    last_sign_in_time = Faker('iso8601', tzinfo=timezone.utc)


class UnverifiedUserFactory(UserFactory):
    """Factory for creating unverified test User instances."""

    email_verified = False
