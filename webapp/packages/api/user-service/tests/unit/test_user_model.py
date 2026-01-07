"""Unit tests for User models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from models.user import User, UsageEntry, UsageInfo, BillingInfo, BasicInfo


pytestmark = pytest.mark.unit


class TestUsageEntry:
    """Test suite for UsageEntry model."""

    def test_usage_entry_creation_with_defaults(self):
        """Test creating a UsageEntry with default values."""
        entry = UsageEntry(responseCost=10.5)

        assert entry.response_cost == 10.5
        assert isinstance(entry.timestamp, datetime)
        assert entry.metadata is None

    def test_usage_entry_with_metadata(self):
        """Test creating a UsageEntry with metadata."""
        metadata = {"model": "gpt-4", "tokens": 100}
        entry = UsageEntry(responseCost=25.0, metadata=metadata)

        assert entry.response_cost == 25.0
        assert entry.metadata == metadata

    def test_usage_entry_alias_mapping(self):
        """Test that camelCase aliases work correctly."""
        entry = UsageEntry(responseCost=15.0)
        data = entry.model_dump(by_alias=True)

        assert "responseCost" in data
        assert data["responseCost"] == 15.0


class TestUsageInfo:
    """Test suite for UsageInfo model."""

    def test_usage_info_defaults(self):
        """Test UsageInfo default values."""
        usage_info = UsageInfo()

        assert usage_info.monthly_allowance == 100.0
        assert usage_info.allowance_reset_date == 0.0
        assert usage_info.spend_remaining == 100.0
        assert usage_info.usage == []

    def test_usage_info_custom_values(self):
        """Test UsageInfo with custom values."""
        usage_info = UsageInfo(
            monthlyAllowance=200.0,
            allowanceResetDate=1234567890.0,
            spendRemaining=150.0,
            usage=[UsageEntry(responseCost=50.0)]
        )

        assert usage_info.monthly_allowance == 200.0
        assert usage_info.allowance_reset_date == 1234567890.0
        assert usage_info.spend_remaining == 150.0
        assert len(usage_info.usage) == 1

    def test_usage_info_accepts_snake_case(self):
        """Test that UsageInfo accepts snake_case field names."""
        usage_info = UsageInfo(
            monthly_allowance=300.0,
            spend_remaining=250.0
        )

        assert usage_info.monthly_allowance == 300.0
        assert usage_info.spend_remaining == 250.0


class TestBillingInfo:
    """Test suite for BillingInfo model."""

    def test_billing_info_defaults(self):
        """Test BillingInfo default values."""
        billing_info = BillingInfo()

        assert billing_info.plan is None
        assert billing_info.status is None

    def test_billing_info_with_values(self):
        """Test BillingInfo with custom values."""
        billing_info = BillingInfo(plan="premium", status="active")

        assert billing_info.plan == "premium"
        assert billing_info.status == "active"


class TestBasicInfo:
    """Test suite for BasicInfo model."""

    def test_basic_info_defaults(self):
        """Test BasicInfo default values."""
        basic_info = BasicInfo()

        assert basic_info.display_name is None
        assert basic_info.email is None

    def test_basic_info_with_values(self):
        """Test BasicInfo with custom values."""
        basic_info = BasicInfo(
            displayName="Test User",
            email="test@example.com"
        )

        assert basic_info.display_name == "Test User"
        assert basic_info.email == "test@example.com"

    def test_basic_info_snake_case_fields(self):
        """Test BasicInfo accepts snake_case field names."""
        basic_info = BasicInfo(
            display_name="Test User",
            email="test@example.com"
        )

        assert basic_info.display_name == "Test User"
        assert basic_info.email == "test@example.com"


class TestUser:
    """Test suite for User model."""

    def test_user_creation_minimal(self):
        """Test creating a User with minimal required fields."""
        user = User(_id="test-user-123")

        assert user.id == "test-user-123"
        assert user.rev is None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        assert isinstance(user.basic_info, BasicInfo)
        assert isinstance(user.billing_info, BillingInfo)
        assert isinstance(user.usage_info, UsageInfo)

    def test_user_creation_full(self):
        """Test creating a User with all fields."""
        now = datetime.utcnow()
        user = User(
            _id="test-user-123",
            _rev="test-rev",
            createdAt=now,
            updatedAt=now,
            basicInfo=BasicInfo(displayName="Test User", email="test@example.com"),
            billingInfo=BillingInfo(plan="premium", status="active"),
            usageInfo=UsageInfo(monthlyAllowance=200.0, spendRemaining=150.0)
        )

        assert user.id == "test-user-123"
        assert user.rev == "test-rev"
        assert user.created_at == now
        assert user.basic_info.display_name == "Test User"
        assert user.billing_info.plan == "premium"
        assert user.usage_info.monthly_allowance == 200.0

    def test_user_missing_id_raises_validation_error(self):
        """Test that creating a User without an ID raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            User()

        assert "id" in str(exc_info.value) or "_id" in str(exc_info.value)

    def test_user_model_dump_with_aliases(self):
        """Test that model_dump uses camelCase aliases."""
        user = User(
            _id="test-user-123",
            basicInfo=BasicInfo(displayName="Test User", email="test@example.com")
        )
        data = user.model_dump(by_alias=True, mode="json")

        assert "_id" in data
        assert "basicInfo" in data
        assert "createdAt" in data
        assert "updatedAt" in data
        assert data["basicInfo"]["displayName"] == "Test User"

    def test_user_from_dict_with_aliases(self):
        """Test creating User from dict with camelCase keys."""
        data = {
            "_id": "test-user-123",
            "createdAt": "2024-01-01T00:00:00",
            "updatedAt": "2024-01-01T00:00:00",
            "basicInfo": {
                "displayName": "Test User",
                "email": "test@example.com"
            },
            "usageInfo": {
                "monthlyAllowance": 200.0,
                "spendRemaining": 175.0
            }
        }
        user = User(**data)

        assert user.id == "test-user-123"
        assert user.basic_info.display_name == "Test User"
        assert user.usage_info.monthly_allowance == 200.0

    def test_user_nested_usage_entries(self):
        """Test User with nested usage entries."""
        user = User(
            _id="test-user-123",
            usageInfo=UsageInfo(
                monthlyAllowance=100.0,
                spendRemaining=50.0,
                usage=[
                    UsageEntry(responseCost=25.0, metadata={"model": "gpt-3.5"}),
                    UsageEntry(responseCost=25.0, metadata={"model": "gpt-4"})
                ]
            )
        )

        assert len(user.usage_info.usage) == 2
        assert user.usage_info.usage[0].response_cost == 25.0
        assert user.usage_info.usage[1].metadata["model"] == "gpt-4"
