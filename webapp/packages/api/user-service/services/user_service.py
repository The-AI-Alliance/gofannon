from datetime import datetime
from typing import Optional, Any, List

from fastapi import HTTPException

from models.user import User, UsageEntry


class UserService:
    def __init__(self, db_service):
        self.db = db_service

    def _create_default_user(self, user_id: str, basic_info: Optional[dict] = None) -> User:
        now = datetime.utcnow()
        basic_info = basic_info or {}
        user = User(
            _id=user_id,
            created_at=now,
            updated_at=now,
            basic_info={
                "displayName": basic_info.get("name") or basic_info.get("displayName"),
                "email": basic_info.get("email"),
            },
        )
        return user

    def get_user(self, user_id: str, basic_info: Optional[dict] = None) -> User:
        try:
            doc = self.db.get("users", user_id)
            return User(**doc)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        user = self._create_default_user(user_id, basic_info)
        return self.save_user(user)

    def list_users(self) -> List[User]:
        return [User(**user_doc) for user_doc in self.db.list_all("users")]

    def save_user(self, user: User) -> User:
        user.updated_at = datetime.utcnow()
        saved = self.db.save("users", user.id, user.model_dump(by_alias=True, mode="json"))
        user.rev = saved.get("rev")
        return user

    def require_allowance(self, user_id: str, minimum_remaining: float = 1.0, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        if user.usage_info.spend_remaining <= minimum_remaining:
            raise HTTPException(status_code=402, detail="Insufficient spend allowance to complete request")
        return user

    def set_monthly_allowance(self, user_id: str, amount: float, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        user.usage_info.monthly_allowance = amount
        if user.usage_info.spend_remaining > amount:
            user.usage_info.spend_remaining = amount
        return self.save_user(user)

    def set_reset_date(self, user_id: str, reset_date: float, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        user.usage_info.allowance_reset_date = reset_date
        return self.save_user(user)

    def reset_allowance(self, user_id: str, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        user.usage_info.spend_remaining = user.usage_info.monthly_allowance
        user.usage_info.usage = []
        return self.save_user(user)

    def update_spend_remaining(self, user_id: str, spend_remaining: float, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        user.usage_info.spend_remaining = spend_remaining
        return self.save_user(user)

    def update_user_usage_info(
        self,
        user_id: str,
        *,
        monthly_allowance: Optional[float] = None,
        allowance_reset_date: Optional[float] = None,
        spend_remaining: Optional[float] = None,
        basic_info: Optional[dict] = None,
    ) -> User:
        user = self.get_user(user_id, basic_info)

        if monthly_allowance is not None:
            user.usage_info.monthly_allowance = monthly_allowance
            if user.usage_info.spend_remaining > monthly_allowance:
                user.usage_info.spend_remaining = monthly_allowance

        if allowance_reset_date is not None:
            user.usage_info.allowance_reset_date = allowance_reset_date

        if spend_remaining is not None:
            user.usage_info.spend_remaining = spend_remaining

        return self.save_user(user)

    def add_usage(self, user_id: str, response_cost: float, metadata: Optional[Any] = None, basic_info: Optional[dict] = None) -> User:
        user = self.get_user(user_id, basic_info)
        user.usage_info.usage.append(UsageEntry(responseCost=response_cost, metadata=metadata))
        user.usage_info.spend_remaining = max(0.0, user.usage_info.spend_remaining - response_cost)
        return self.save_user(user)


_user_service_instance: Optional[UserService] = None


def get_user_service(db_service):
    global _user_service_instance
    if _user_service_instance is None or _user_service_instance.db is not db_service:
        _user_service_instance = UserService(db_service)
    return _user_service_instance
