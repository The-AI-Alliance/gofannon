# webapp/packages/api/user-service/services/data_store_service.py

"""
Service for managing agent data store operations.

The data store allows agents to persist and share data across executions.
Data is scoped to users - all agents owned by a user can access the same data pool.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from services.database_service import DatabaseService


# Database/collection name for data store records
DATA_STORE_DB = "agent_data_store"


class DataStoreService:
    """Service for agent data store operations."""
    
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def _make_doc_id(self, user_id: str, namespace: str, key: str) -> str:
        """Generate document ID from composite key."""
        import base64
        safe_key = base64.urlsafe_b64encode(key.encode()).decode()
        return f"{user_id}:{namespace}:{safe_key}"
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return sys.getsizeof(json.dumps(value))
        except (TypeError, ValueError):
            return 0
    
    def get(
        self, 
        user_id: str, 
        namespace: str, 
        key: str,
        agent_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a value from the data store."""
        doc_id = self._make_doc_id(user_id, namespace, key)
        
        try:
            doc = self.db.get(DATA_STORE_DB, doc_id)
            
            if agent_name and doc:
                doc["lastAccessedByAgent"] = agent_name
                doc["lastAccessedAt"] = datetime.utcnow().isoformat()
                doc["accessCount"] = doc.get("accessCount", 0) + 1
                self.db.save(DATA_STORE_DB, doc_id, doc)
            
            return doc
        except HTTPException as e:
            if e.status_code == 404:
                return None
            raise
    
    def set(
        self,
        user_id: str,
        namespace: str,
        key: str,
        value: Any,
        agent_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Set a value in the data store."""
        doc_id = self._make_doc_id(user_id, namespace, key)
        now = datetime.utcnow()
        
        existing = None
        try:
            existing = self.db.get(DATA_STORE_DB, doc_id)
        except HTTPException as e:
            if e.status_code != 404:
                raise
        
        if existing:
            record_data = {
                **existing,
                "value": value,
                "updatedAt": now.isoformat(),
            }
            if metadata:
                record_data["metadata"] = {**existing.get("metadata", {}), **metadata}
            if agent_name:
                record_data["lastAccessedByAgent"] = agent_name
                record_data["lastAccessedAt"] = now.isoformat()
        else:
            record_data = {
                "_id": doc_id,
                "userId": user_id,
                "namespace": namespace,
                "key": key,
                "value": value,
                "metadata": metadata or {},
                "createdByAgent": agent_name,
                "lastAccessedByAgent": agent_name,
                "accessCount": 0,
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "lastAccessedAt": now.isoformat() if agent_name else None,
            }
        
        saved = self.db.save(DATA_STORE_DB, doc_id, record_data)
        record_data["_rev"] = saved.get("rev")
        return record_data
    
    def delete(self, user_id: str, namespace: str, key: str) -> bool:
        """Delete a value from the data store."""
        doc_id = self._make_doc_id(user_id, namespace, key)
        
        try:
            self.db.delete(DATA_STORE_DB, doc_id)
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            raise
    
    def list_keys(
        self,
        user_id: str,
        namespace: str,
        prefix: Optional[str] = None
    ) -> List[str]:
        """List all keys in a namespace."""
        all_docs = self.db.list_all(DATA_STORE_DB)
        
        keys = []
        for doc in all_docs:
            if doc.get("userId") == user_id and doc.get("namespace") == namespace:
                key = doc.get("key", "")
                if prefix is None or key.startswith(prefix):
                    keys.append(key)
        
        return sorted(keys)
    
    def list_namespaces(self, user_id: str) -> List[str]:
        """List all namespaces for a user.
        
        Returns a sorted list of all unique namespace names that contain
        data for the specified user. Useful for discovering what data
        exists before querying specific namespaces.
        """
        all_docs = self.db.list_all(DATA_STORE_DB)
        namespaces = set()
        for doc in all_docs:
            if doc.get("userId") == user_id:
                namespaces.add(doc.get("namespace", "default"))
        return sorted(namespaces)
    
    def get_many(
        self,
        user_id: str,
        namespace: str,
        keys: List[str],
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple values at once."""
        results = {}
        for key in keys:
            record = self.get(user_id, namespace, key, agent_name)
            if record:
                results[key] = record.get("value")
        return results
    
    def set_many(
        self,
        user_id: str,
        items: List[Tuple[str, str, Any, Optional[Dict[str, Any]]]],
        agent_name: Optional[str] = None
    ) -> int:
        """Set multiple values at once."""
        count = 0
        for namespace, key, value, metadata in items:
            self.set(user_id, namespace, key, value, agent_name, metadata)
            count += 1
        return count
    
    def clear_namespace(self, user_id: str, namespace: str) -> int:
        """Delete all records in a namespace."""
        keys = self.list_keys(user_id, namespace)
        count = 0
        for key in keys:
            if self.delete(user_id, namespace, key):
                count += 1
        return count


class AgentDataStoreProxy:
    """
    Proxy class injected into agent execution context.
    Provides a clean API for agents to interact with the data store.
    """
    
    def __init__(
        self,
        service: DataStoreService,
        user_id: str,
        agent_name: str,
        default_namespace: str = "default"
    ):
        self._service = service
        self._user_id = user_id
        self._agent_name = agent_name
        self._namespace = default_namespace
    
    def use_namespace(self, namespace: str) -> "AgentDataStoreProxy":
        """Return a new proxy scoped to a specific namespace."""
        return AgentDataStoreProxy(
            self._service,
            self._user_id,
            self._agent_name,
            namespace
        )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key."""
        record = self._service.get(
            self._user_id, 
            self._namespace, 
            key, 
            self._agent_name
        )
        return record.get("value") if record else default
    
    def set(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set a value by key."""
        self._service.set(
            self._user_id,
            self._namespace,
            key,
            value,
            self._agent_name,
            metadata
        )
    
    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        return self._service.delete(self._user_id, self._namespace, key)
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        return self._service.list_keys(self._user_id, self._namespace, prefix)
    
    def list_namespaces(self) -> List[str]:
        """List all namespaces containing data for this user.
        
        Returns a sorted list of namespace names. Use this to discover
        what data exists before querying specific namespaces.
        
        Example:
            namespaces = data_store.list_namespaces()
            # Returns: ["default", "files:apache/repo", "summary:apache/repo", ...]
        """
        return self._service.list_namespaces(self._user_id)
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once."""
        return self._service.get_many(
            self._user_id, 
            self._namespace, 
            keys, 
            self._agent_name
        )
    
    def set_many(self, items: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> int:
        """Set multiple values at once."""
        item_list = [
            (self._namespace, key, value, metadata)
            for key, value in items.items()
        ]
        return self._service.set_many(self._user_id, item_list, self._agent_name)
    
    def clear(self) -> int:
        """Clear all data in the current namespace."""
        return self._service.clear_namespace(self._user_id, self._namespace)


def get_data_store_service(db: DatabaseService) -> DataStoreService:
    """Factory function to create DataStoreService instance."""
    return DataStoreService(db)