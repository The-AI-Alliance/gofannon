from datetime import datetime
from typing import Optional, Any, List, Dict

from fastapi import HTTPException

from models.user import User, UsageEntry, ApiKeys


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

    def get_api_keys(self, user_id: str, basic_info: Optional[dict] = None) -> ApiKeys:
        """Get the user's API keys (masked for security)"""
        user = self.get_user(user_id, basic_info)
        return user.api_keys

    def update_api_key(self, user_id: str, provider: str, api_key: str, basic_info: Optional[dict] = None) -> User:
        """Update a specific API key for a provider"""
        user = self.get_user(user_id, basic_info)
        
        # Map provider names to ApiKeys field names
        provider_key_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "gemini": "gemini_api_key",
            "perplexity": "perplexity_api_key",
        }
        
        key_field = provider_key_map.get(provider)
        if not key_field:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
        # Update the specific API key
        setattr(user.api_keys, key_field, api_key)
        return self.save_user(user)

    def delete_api_key(self, user_id: str, provider: str, basic_info: Optional[dict] = None) -> User:
        """Delete (clear) a specific API key for a provider"""
        user = self.get_user(user_id, basic_info)
        
        # Map provider names to ApiKeys field names
        provider_key_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "gemini": "gemini_api_key",
            "perplexity": "perplexity_api_key",
        }
        
        key_field = provider_key_map.get(provider)
        if not key_field:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
        # Clear the specific API key
        setattr(user.api_keys, key_field, None)
        return self.save_user(user)

    def get_effective_api_key(self, user_id: str, provider: str, basic_info: Optional[dict] = None) -> Optional[str]:
        """
        Get the effective API key for a provider.
        First checks user's stored keys, then falls back to environment variables.
        Returns None if no key is available.
        """
        import os
        from config.provider_config import PROVIDER_CONFIG
        
        user = self.get_user(user_id, basic_info)
        
        # Map provider names to ApiKeys field names
        provider_key_map = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "gemini": "gemini_api_key",
            "perplexity": "perplexity_api_key",
        }
        
        # First, check user's stored API keys
        key_field = provider_key_map.get(provider)
        if key_field:
            user_key = getattr(user.api_keys, key_field)
            if user_key:
                return user_key
        
        # Fall back to environment variable
        provider_config = PROVIDER_CONFIG.get(provider, {})
        env_var = provider_config.get("api_key_env_var")
        if env_var:
            return os.getenv(env_var)
        
        return None


_user_service_instance: Optional[UserService] = None


def get_user_service(db_service):
    global _user_service_instance
    if _user_service_instance is None or _user_service_instance.db is not db_service:
        _user_service_instance = UserService(db_service)
    return _user_service_instance
