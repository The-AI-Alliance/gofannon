"""Factory classes for generating test Chat data."""
import factory
from factory import Faker


class ChatRequestFactory(factory.Factory):
    """Factory for creating test ChatRequest instances."""

    class Meta:
        model = dict

    message = Faker('sentence')
    provider = 'openai'
    model = 'gpt-4'
    agent_id = Faker('uuid4')
    session_id = Faker('uuid4')
    temperature = 0.7
    max_tokens = 1000


class ChatResponseFactory(factory.Factory):
    """Factory for creating test ChatResponse instances."""

    class Meta:
        model = dict

    message = Faker('paragraph')
    session_id = Faker('uuid4')
    agent_id = Faker('uuid4')
    model = 'gpt-4'
    provider = 'openai'
    usage = factory.LazyFunction(
        lambda: {
            'prompt_tokens': 10,
            'completion_tokens': 50,
            'total_tokens': 60
        }
    )
