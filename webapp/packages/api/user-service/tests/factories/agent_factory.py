"""Factory classes for generating test Agent data."""
import factory
from factory import Faker, LazyAttribute
from datetime import datetime, timezone


class AgentFactory(factory.Factory):
    """Factory for creating test Agent instances."""

    class Meta:
        model = dict

    id = Faker('uuid4')
    user_id = Faker('uuid4')
    name = Faker('catch_phrase')
    description = Faker('sentence')
    api_specs = factory.LazyFunction(
        lambda: [f"https://api.{Faker('domain_name').generate()}/openapi.json"]
    )
    code = LazyAttribute(
        lambda obj: f"# Agent: {obj.name}\nprint('Agent code here')"
    )
    created_at = Faker('iso8601', tzinfo=timezone.utc)
    updated_at = Faker('iso8601', tzinfo=timezone.utc)
    is_deployed = False
    deployment_url = None


class DeployedAgentFactory(AgentFactory):
    """Factory for creating deployed test Agent instances."""

    is_deployed = True
    deployment_url = Faker('url')


class CreateAgentRequestFactory(factory.Factory):
    """Factory for creating CreateAgentRequest test data."""

    class Meta:
        model = dict

    name = Faker('catch_phrase')
    description = Faker('sentence')
    api_specs = factory.LazyFunction(
        lambda: [f"https://api.{Faker('domain_name').generate()}/openapi.json"]
    )


class UpdateAgentRequestFactory(factory.Factory):
    """Factory for updating Agent test data."""

    class Meta:
        model = dict

    name = Faker('catch_phrase')
    description = Faker('sentence')
    api_specs = factory.LazyFunction(
        lambda: [f"https://api.{Faker('domain_name').generate()}/openapi.json"]
    )
    code = Faker('text', max_nb_chars=200)
