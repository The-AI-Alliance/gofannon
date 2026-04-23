# webapp/packages/api/user-service/models/data_store.py
"""Pydantic request/response models for the data store HTTP API.

The DataStoreService (services/data_store_service.py) operates on raw dicts
because it's also used by the agent runtime. These models wrap the service
for REST endpoints, applying camelCase aliases for the frontend and light
validation on incoming payloads.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class DataStoreRecord(BaseModel):
    """A single record in the data store, as returned to the UI."""
    id: str = Field(..., alias="_id")
    user_id: str = Field(..., alias="userId")
    namespace: str
    key: str
    value: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_by_agent: Optional[str] = Field(None, alias="createdByAgent")
    last_accessed_by_agent: Optional[str] = Field(None, alias="lastAccessedByAgent")
    access_count: int = Field(0, alias="accessCount")
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    last_accessed_at: Optional[str] = Field(None, alias="lastAccessedAt")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class NamespaceStats(BaseModel):
    """Aggregate stats for a namespace, used by the list/overview views."""
    namespace: str
    record_count: int = Field(..., alias="recordCount")
    size_bytes: int = Field(..., alias="sizeBytes")
    # Agents that have written to or read from this namespace. Derived from
    # createdByAgent + lastAccessedByAgent across all records.
    agents: List[str] = Field(default_factory=list)
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class NamespaceListResponse(BaseModel):
    """Response shape for GET /data-store/namespaces."""
    namespaces: List[NamespaceStats]
    total_record_count: int = Field(..., alias="totalRecordCount")
    total_size_bytes: int = Field(..., alias="totalSizeBytes")

    model_config = ConfigDict(populate_by_name=True)


class SetRecordRequest(BaseModel):
    """Body for PUT /data-store/namespaces/{namespace}/records/{key}.

    Used only for admin edits in the viewer UI. Agent writes go through
    the AgentDataStoreProxy directly during sandbox execution.
    """
    value: Any
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(populate_by_name=True)


class ClearNamespaceResponse(BaseModel):
    """Response for DELETE /data-store/namespaces/{namespace}."""
    namespace: str
    deleted_count: int = Field(..., alias="deletedCount")

    model_config = ConfigDict(populate_by_name=True)
