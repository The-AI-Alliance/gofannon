"""Unit tests for UserService."""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from fastapi import HTTPException

from services.user_service import UserService, get_user_service
from models.user import User, UsageEntry
from tests.factories.user_factory import UserFactory


pytestmark = pytest.mark.unit


class TestUserService:
    """Test suite for UserService class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = Mock()
        db.get = Mock()
        db.save = Mock(return_value={"rev": "test-rev"})
        db.list_all = Mock(return_value=[])
        return db

    @pytest.fixture
    def user_service(self, mock_db):
        """Create a UserService instance with mock database."""
        return UserService(mock_db)

    def test_create_default_user_with_no_basic_info(self, user_service):
        """Test creating a default user with no basic info."""
        user = user_service._create_default_user("test-user-id")

        assert user.id == "test-user-id"
        assert user.basic_info.display_name is None
        assert user.basic_info.email is None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_create_default_user_with_basic_info(self, user_service):
        """Test creating a default user with basic info."""
        basic_info = {
            "name": "Test User",
            "email": "test@example.com"
        }
        user = user_service._create_default_user("test-user-id", basic_info)

        assert user.id == "test-user-id"
        assert user.basic_info.display_name == "Test User"
        assert user.basic_info.email == "test@example.com"

    def test_get_user_existing(self, user_service, mock_db):
        """Test getting an existing user."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        user = user_service.get_user("test-user-id")

        mock_db.get.assert_called_once_with("users", "test-user-id")
        assert user.id == user_data["_id"]

    def test_get_user_not_found_creates_new(self, user_service, mock_db):
        """Test that getting a non-existent user creates a new one."""
        mock_db.get.side_effect = HTTPException(status_code=404, detail="Not found")

        user = user_service.get_user("new-user-id")

        assert user.id == "new-user-id"
        mock_db.save.assert_called_once()

    def test_get_user_other_error_raises(self, user_service, mock_db):
        """Test that non-404 errors are raised."""
        mock_db.get.side_effect = HTTPException(status_code=500, detail="Server error")

        with pytest.raises(HTTPException) as exc_info:
            user_service.get_user("test-user-id")

        assert exc_info.value.status_code == 500

    def test_list_users(self, user_service, mock_db):
        """Test listing all users."""
        users_data = [UserFactory.build() for _ in range(3)]
        mock_db.list_all.return_value = users_data

        users = user_service.list_users()

        mock_db.list_all.assert_called_once_with("users")
        assert len(users) == 3
        assert all(isinstance(user, User) for user in users)

    def test_save_user(self, user_service, mock_db):
        """Test saving a user updates the updated_at field."""
        user_data = UserFactory.build()
        user = User(**user_data)
        original_updated_at = user.updated_at

        saved_user = user_service.save_user(user)

        assert saved_user.updated_at > original_updated_at
        assert saved_user.rev == "test-rev"
        mock_db.save.assert_called_once()

    def test_require_allowance_sufficient(self, user_service, mock_db):
        """Test require_allowance when user has sufficient allowance."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        user = user_service.require_allowance("test-user-id", minimum_remaining=1.0)

        assert user.id == user_data["_id"]

    def test_require_allowance_insufficient(self, user_service, mock_db):
        """Test require_allowance raises error when insufficient allowance."""
        user_data = UserFactory.build()
        # Simulate a user with no remaining allowance
        user = User(**user_data)
        user.usage_info.spend_remaining = 0.5
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        with pytest.raises(HTTPException) as exc_info:
            user_service.require_allowance("test-user-id", minimum_remaining=1.0)

        assert exc_info.value.status_code == 402
        assert "Insufficient spend allowance" in exc_info.value.detail

    def test_set_monthly_allowance(self, user_service, mock_db):
        """Test setting monthly allowance."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        updated_user = user_service.set_monthly_allowance("test-user-id", 100.0)

        assert updated_user.usage_info.monthly_allowance == 100.0
        mock_db.save.assert_called_once()

    def test_set_monthly_allowance_adjusts_spend_remaining(self, user_service, mock_db):
        """Test that setting a lower allowance adjusts spend_remaining."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.usage_info.spend_remaining = 200.0
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        updated_user = user_service.set_monthly_allowance("test-user-id", 50.0)

        assert updated_user.usage_info.monthly_allowance == 50.0
        assert updated_user.usage_info.spend_remaining == 50.0

    def test_reset_allowance(self, user_service, mock_db):
        """Test resetting user allowance."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.usage_info.monthly_allowance = 100.0
        user.usage_info.spend_remaining = 30.0
        user.usage_info.usage = [UsageEntry(responseCost=10.0), UsageEntry(responseCost=20.0)]
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        reset_user = user_service.reset_allowance("test-user-id")

        assert reset_user.usage_info.spend_remaining == 100.0
        assert len(reset_user.usage_info.usage) == 0

    def test_update_spend_remaining(self, user_service, mock_db):
        """Test updating spend_remaining directly."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        updated_user = user_service.update_spend_remaining("test-user-id", 75.0)

        assert updated_user.usage_info.spend_remaining == 75.0
        mock_db.save.assert_called_once()

    def test_add_usage(self, user_service, mock_db):
        """Test adding usage entry and deducting from remaining allowance."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.usage_info.spend_remaining = 100.0
        initial_usage_count = len(user.usage_info.usage)
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        updated_user = user_service.add_usage(
            "test-user-id",
            response_cost=25.0,
            metadata={"model": "gpt-4"}
        )

        assert len(updated_user.usage_info.usage) == initial_usage_count + 1
        assert updated_user.usage_info.spend_remaining == 75.0
        assert updated_user.usage_info.usage[-1].response_cost == 25.0

    def test_add_usage_prevents_negative_remaining(self, user_service, mock_db):
        """Test that add_usage prevents negative spend_remaining."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.usage_info.spend_remaining = 10.0
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        updated_user = user_service.add_usage("test-user-id", response_cost=25.0)

        assert updated_user.usage_info.spend_remaining == 0.0

    def test_update_user_usage_info_all_fields(self, user_service, mock_db):
        """Test updating all usage info fields at once."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        updated_user = user_service.update_user_usage_info(
            "test-user-id",
            monthly_allowance=200.0,
            allowance_reset_date=1234567890.0,
            spend_remaining=150.0
        )

        assert updated_user.usage_info.monthly_allowance == 200.0
        assert updated_user.usage_info.allowance_reset_date == 1234567890.0
        assert updated_user.usage_info.spend_remaining == 150.0
        mock_db.save.assert_called_once()

    def test_set_reset_date(self, user_service, mock_db):
        """Test setting the allowance reset date."""
        user_data = UserFactory.build()
        mock_db.get.return_value = user_data

        updated_user = user_service.set_reset_date("test-user-id", 9876543210.0)

        assert updated_user.usage_info.allowance_reset_date == 9876543210.0
        mock_db.save.assert_called_once()

    def test_update_user_usage_info_caps_spend_remaining(self, user_service, mock_db):
        """Test update_user_usage_info caps spend_remaining when allowance drops."""
        user_data = UserFactory.build()
        user = User(**user_data)
        user.usage_info.spend_remaining = 120.0
        mock_db.get.return_value = user.model_dump(by_alias=True, mode="json")

        updated_user = user_service.update_user_usage_info(
            "test-user-id",
            monthly_allowance=100.0,
        )

        assert updated_user.usage_info.monthly_allowance == 100.0
        assert updated_user.usage_info.spend_remaining == 100.0

    def test_get_user_service_singleton(self, mock_db):
        """Test that get_user_service returns a singleton instance."""
        service1 = get_user_service(mock_db)
        service2 = get_user_service(mock_db)

        assert service1 is service2
