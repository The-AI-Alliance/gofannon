"""Factory classes for generating test User data."""
import factory
from factory import Faker
from faker import Faker as FakerLib


faker = FakerLib()


class UserFactory(factory.Factory):
    """Factory for creating test User instances."""

    class Meta:
        model = dict

    _id = Faker("uuid4")
    _rev = Faker("uuid4")
    createdAt = Faker("date_time")
    updatedAt = Faker("date_time")
    basicInfo = factory.LazyFunction(
        lambda: {
            "displayName": faker.name(),
            "email": faker.email(),
        }
    )
    billingInfo = factory.LazyFunction(lambda: {"plan": None, "status": None})
    usageInfo = factory.LazyFunction(
        lambda: {
            "monthlyAllowance": 100.0,
            "allowanceResetDate": 0.0,
            "spendRemaining": 100.0,
            "usage": [],
        }
    )


class UnverifiedUserFactory(UserFactory):
    """Factory for creating unverified test User instances."""

    email_verified = False
