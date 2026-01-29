from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from pydantic.config import ConfigDict


class UsageEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_cost: float = Field(alias="responseCost")
    metadata: Optional[Any] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class UsageInfo(BaseModel):
    monthly_allowance: float = Field(default=100.0, alias="monthlyAllowance")
    allowance_reset_date: float = Field(default=0.0, alias="allowanceResetDate")
    spend_remaining: float = Field(default=100.0, alias="spendRemaining")
    usage: List[UsageEntry] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class BillingInfo(BaseModel):
    plan: Optional[str] = None
    status: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class BasicInfo(BaseModel):
    display_name: Optional[str] = Field(default=None, alias="displayName")
    email: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ApiKeys(BaseModel):
    """User-specific API keys for LLM providers"""
    openai_api_key: Optional[str] = Field(default=None, alias="openaiApiKey")
    anthropic_api_key: Optional[str] = Field(default=None, alias="anthropicApiKey")
    gemini_api_key: Optional[str] = Field(default=None, alias="geminiApiKey")
    perplexity_api_key: Optional[str] = Field(default=None, alias="perplexityApiKey")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class User(BaseModel):
    id: str = Field(alias="_id")
    rev: Optional[str] = Field(default=None, alias="_rev")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")
    basic_info: BasicInfo = Field(default_factory=BasicInfo, alias="basicInfo")
    billing_info: BillingInfo = Field(default_factory=BillingInfo, alias="billingInfo")
    usage_info: UsageInfo = Field(default_factory=UsageInfo, alias="usageInfo")
    api_keys: ApiKeys = Field(default_factory=ApiKeys, alias="apiKeys")

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
