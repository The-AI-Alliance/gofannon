# tests/unit/services/test_data_store_service.py

"""
Unit tests for the Agent Data Store service.
"""

import base64
import pytest
from unittest.mock import Mock, MagicMock, call, patch
from datetime import datetime
from fastapi import HTTPException

from services.data_store_service import (
    DataStoreService,
    AgentDataStoreProxy,
    get_data_store_service,
    DATA_STORE_DB,
    _STANDARD_INDEXES,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock DatabaseService.

    ``find`` is wired to fall back to ``list_all`` with in-Python
    filtering (mirroring the real base-class default) so that existing
    tests that set ``mock_db.list_all.return_value`` keep working now
    that the service methods call ``find`` instead of ``list_all``.
    """
    db = Mock()

    def _find(db_name, selector, fields=None, limit=10000):
        all_docs = db.list_all(db_name)
        results = []
        for doc in all_docs:
            if all(doc.get(k) == v for k, v in selector.items()):
                if fields:
                    results.append({f: doc.get(f) for f in fields})
                else:
                    results.append(doc)
                if len(results) >= limit:
                    break
        return results

    db.find.side_effect = _find
    # ensure_index is a no-op by default
    db.ensure_index.return_value = None
    return db


@pytest.fixture
def data_store_service(mock_db):
    """Create a DataStoreService with mocked database."""
    return DataStoreService(mock_db)


@pytest.fixture
def agent_proxy(data_store_service):
    """Create an AgentDataStoreProxy for testing."""
    return AgentDataStoreProxy(
        service=data_store_service,
        user_id="user-123",
        agent_name="test-agent",
        default_namespace="default"
    )


# =============================================================================
# DataStoreService Tests
# =============================================================================

class TestDataStoreService:
    """Tests for DataStoreService class."""

    def test_make_doc_id(self, data_store_service):
        """Test document ID generation."""
        doc_id = data_store_service._make_doc_id("user-123", "my-namespace", "my-key")
        
        # Should contain user_id and namespace
        assert doc_id.startswith("user-123:my-namespace:")
        # Key should be base64 encoded
        assert "my-key" not in doc_id  # Raw key shouldn't appear

    def test_make_doc_id_special_characters(self, data_store_service):
        """Test document ID generation with special characters in key."""
        doc_id = data_store_service._make_doc_id("user-123", "ns", "path/to/file.py")
        
        assert doc_id.startswith("user-123:ns:")
        # Should not contain raw path separators
        assert "/to/" not in doc_id

    def test_get_existing_key(self, data_store_service, mock_db):
        """Test getting an existing key."""
        mock_db.get.return_value = {
            "_id": "doc-id",
            "userId": "user-123",
            "namespace": "default",
            "key": "my-key",
            "value": {"data": "test"},
            "accessCount": 5,
        }
        
        result = data_store_service.get("user-123", "default", "my-key")
        
        assert result is not None
        assert result["value"] == {"data": "test"}
        mock_db.get.assert_called_once()

    def test_get_missing_key(self, data_store_service, mock_db):
        """Test getting a non-existent key returns None."""
        mock_db.get.side_effect = HTTPException(status_code=404, detail="Not found")
        
        result = data_store_service.get("user-123", "default", "missing-key")
        
        assert result is None

    def test_get_with_agent_name_updates_access(self, data_store_service, mock_db):
        """Test that providing agent_name updates access metadata."""
        mock_db.get.return_value = {
            "_id": "doc-id",
            "userId": "user-123",
            "namespace": "default",
            "key": "my-key",
            "value": "test",
            "accessCount": 5,
        }
        
        data_store_service.get("user-123", "default", "my-key", agent_name="reader-agent")
        
        # Should save updated document with access info
        mock_db.save.assert_called_once()
        saved_doc = mock_db.save.call_args[0][2]
        assert saved_doc["lastAccessedByAgent"] == "reader-agent"
        assert saved_doc["accessCount"] == 6

    def test_set_new_key(self, data_store_service, mock_db):
        """Test setting a new key."""
        mock_db.get.side_effect = HTTPException(status_code=404, detail="Not found")
        mock_db.save.return_value = {"rev": "1-abc123"}
        
        result = data_store_service.set(
            "user-123", "default", "new-key", {"value": "data"}, "writer-agent"
        )
        
        assert result["key"] == "new-key"
        assert result["value"] == {"value": "data"}
        assert result["createdByAgent"] == "writer-agent"
        mock_db.save.assert_called_once()

    def test_set_existing_key_updates(self, data_store_service, mock_db):
        """Test setting an existing key updates it."""
        mock_db.get.return_value = {
            "_id": "doc-id",
            "userId": "user-123",
            "namespace": "default",
            "key": "existing-key",
            "value": "old-value",
            "metadata": {"old": "meta"},
            "createdAt": "2026-01-01T00:00:00",
        }
        mock_db.save.return_value = {"rev": "2-def456"}
        
        result = data_store_service.set(
            "user-123", "default", "existing-key", "new-value", metadata={"new": "meta"}
        )
        
        assert result["value"] == "new-value"
        # Metadata should be merged
        assert result["metadata"]["old"] == "meta"
        assert result["metadata"]["new"] == "meta"

    def test_delete_existing_key(self, data_store_service, mock_db):
        """Test deleting an existing key."""
        mock_db.delete.return_value = None
        
        result = data_store_service.delete("user-123", "default", "my-key")
        
        assert result is True
        mock_db.delete.assert_called_once()

    def test_delete_missing_key(self, data_store_service, mock_db):
        """Test deleting a non-existent key returns False."""
        mock_db.delete.side_effect = HTTPException(status_code=404, detail="Not found")
        
        result = data_store_service.delete("user-123", "default", "missing-key")
        
        assert result is False

    def test_list_keys(self, data_store_service, mock_db):
        """Test listing keys in a namespace."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "key-a"},
            {"userId": "user-123", "namespace": "default", "key": "key-b"},
            {"userId": "user-123", "namespace": "other", "key": "key-c"},
            {"userId": "other-user", "namespace": "default", "key": "key-d"},
        ]
        
        result = data_store_service.list_keys("user-123", "default")
        
        assert result == ["key-a", "key-b"]

    def test_list_keys_with_prefix(self, data_store_service, mock_db):
        """Test listing keys with prefix filter."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "file:a.py"},
            {"userId": "user-123", "namespace": "default", "key": "file:b.py"},
            {"userId": "user-123", "namespace": "default", "key": "cache:data"},
        ]
        
        result = data_store_service.list_keys("user-123", "default", prefix="file:")
        
        assert result == ["file:a.py", "file:b.py"]

    def test_list_namespaces(self, data_store_service, mock_db):
        """Test listing all namespaces for a user."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "key-1"},
            {"userId": "user-123", "namespace": "files:repo-a", "key": "key-2"},
            {"userId": "user-123", "namespace": "files:repo-a", "key": "key-3"},
            {"userId": "user-123", "namespace": "summary:repo-a", "key": "key-4"},
            {"userId": "other-user", "namespace": "other-ns", "key": "key-5"},
        ]
        
        result = data_store_service.list_namespaces("user-123")
        
        # Should be sorted and unique
        assert result == ["default", "files:repo-a", "summary:repo-a"]

    def test_list_namespaces_empty(self, data_store_service, mock_db):
        """Test listing namespaces when user has no data."""
        mock_db.list_all.return_value = [
            {"userId": "other-user", "namespace": "default", "key": "key-1"},
        ]
        
        result = data_store_service.list_namespaces("user-123")
        
        assert result == []

    def test_list_namespaces_handles_missing_namespace(self, data_store_service, mock_db):
        """Test that missing namespace field defaults to 'default'."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "key": "key-1"},  # No namespace field
            {"userId": "user-123", "namespace": "custom", "key": "key-2"},
        ]
        
        result = data_store_service.list_namespaces("user-123")
        
        assert "default" in result
        assert "custom" in result

    def test_list_namespaces_handles_none_namespace(self, data_store_service, mock_db):
        """Test that None namespace field defaults to 'default'.

        When find() uses a field projection, CouchDB may return
        {"namespace": null} for documents stored without the field.
        """
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": None, "key": "key-1"},
            {"userId": "user-123", "namespace": "custom", "key": "key-2"},
        ]

        result = data_store_service.list_namespaces("user-123")

        assert "default" in result
        assert "custom" in result
        assert None not in result

    def test_get_many(self, data_store_service, mock_db):
        """Test getting multiple values at once."""
        key_a_b64 = base64.urlsafe_b64encode(b"key-a").decode()
        key_b_b64 = base64.urlsafe_b64encode(b"key-b").decode()
        
        def mock_get(db_name, doc_id):
            if key_a_b64 in doc_id:
                return {"value": "value-a"}
            elif key_b_b64 in doc_id:
                return {"value": "value-b"}
            raise HTTPException(status_code=404)
        
        mock_db.get.side_effect = mock_get
        
        result = data_store_service.get_many(
            "user-123", "default", ["key-a", "key-b", "key-c"]
        )
        
        assert result == {"key-a": "value-a", "key-b": "value-b"}

    def test_set_many(self, data_store_service, mock_db):
        """Test setting multiple values at once."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        
        items = [
            ("ns1", "key-a", "value-a", None),
            ("ns2", "key-b", "value-b", {"meta": "data"}),
        ]
        
        count = data_store_service.set_many("user-123", items, "writer-agent")
        
        assert count == 2
        assert mock_db.save.call_count == 2

    def test_clear_namespace(self, data_store_service, mock_db):
        """Test clearing all data in a namespace."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "temp", "key": "key-a"},
            {"userId": "user-123", "namespace": "temp", "key": "key-b"},
            {"userId": "user-123", "namespace": "keep", "key": "key-c"},
        ]
        mock_db.delete.return_value = None
        
        count = data_store_service.clear_namespace("user-123", "temp")
        
        assert count == 2
        assert mock_db.delete.call_count == 2


# =============================================================================
# Indexed Query Tests
# =============================================================================

class TestIndexedQueries:
    """Tests for find()-based queries and index management."""

    def test_list_keys_uses_find(self, data_store_service, mock_db):
        """Test that list_keys calls find() with correct selector."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "a"},
        ]

        data_store_service.list_keys("user-123", "default")

        mock_db.find.assert_called_once_with(
            DATA_STORE_DB,
            {"userId": "user-123", "namespace": "default"},
            fields=["key"],
        )

    def test_list_namespaces_uses_find(self, data_store_service, mock_db):
        """Test that list_namespaces calls find() with correct selector."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "ns-a", "key": "k"},
        ]

        data_store_service.list_namespaces("user-123")

        mock_db.find.assert_called_once_with(
            DATA_STORE_DB,
            {"userId": "user-123"},
            fields=["namespace"],
        )

    def test_list_keys_find_returns_projected_docs(self, mock_db):
        """Test list_keys works when find() returns projected docs (key only)."""
        mock_db.find.side_effect = None
        mock_db.find.return_value = [
            {"key": "alpha"},
            {"key": "beta"},
            {"key": "gamma"},
        ]

        service = DataStoreService(mock_db)
        result = service.list_keys("user-123", "default")

        assert result == ["alpha", "beta", "gamma"]

    def test_list_namespaces_find_returns_projected_docs(self, mock_db):
        """Test list_namespaces works when find() returns projected docs."""
        mock_db.find.side_effect = None
        mock_db.find.return_value = [
            {"namespace": "files:repo"},
            {"namespace": "files:repo"},  # duplicate
            {"namespace": "summary:repo"},
            {"namespace": None},  # missing namespace
        ]

        service = DataStoreService(mock_db)
        result = service.list_namespaces("user-123")

        assert result == ["default", "files:repo", "summary:repo"]


# =============================================================================
# get_all Tests
# =============================================================================

class TestGetAll:
    """Tests for the get_all method."""

    def test_get_all_returns_all_keys_in_namespace(self, data_store_service, mock_db):
        """Test get_all returns all key-value pairs from a namespace."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "files:repo", "key": "src/a.py", "value": "content-a"},
            {"userId": "user-123", "namespace": "files:repo", "key": "src/b.py", "value": "content-b"},
            {"userId": "user-123", "namespace": "other", "key": "unrelated", "value": "skip"},
        ]

        result = data_store_service.get_all("user-123", "files:repo")

        assert result == {
            "src/a.py": "content-a",
            "src/b.py": "content-b",
        }

    def test_get_all_empty_namespace(self, data_store_service, mock_db):
        """Test get_all returns empty dict for namespace with no data."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "other", "key": "k", "value": "v"},
        ]

        result = data_store_service.get_all("user-123", "empty-ns")

        assert result == {}

    def test_get_all_uses_find_without_projection(self, data_store_service, mock_db):
        """Test get_all calls find() without field projection (needs full docs)."""
        mock_db.list_all.return_value = []

        data_store_service.get_all("user-123", "files:repo")

        mock_db.find.assert_called_once_with(
            DATA_STORE_DB,
            {"userId": "user-123", "namespace": "files:repo"},
        )

    def test_get_all_updates_access_metadata(self, data_store_service, mock_db):
        """Test get_all updates access tracking when agent_name provided."""
        mock_db.list_all.return_value = [
            {
                "_id": "doc-1",
                "userId": "user-123",
                "namespace": "ns",
                "key": "k1",
                "value": "v1",
                "accessCount": 3,
            },
        ]
        mock_db.save.return_value = {"rev": "2-abc"}

        data_store_service.get_all("user-123", "ns", agent_name="reader")

        mock_db.save.assert_called_once()
        saved_doc = mock_db.save.call_args[0][2]
        assert saved_doc["lastAccessedByAgent"] == "reader"
        assert saved_doc["accessCount"] == 4

    def test_get_all_skips_access_tracking_without_agent(self, data_store_service, mock_db):
        """Test get_all skips access updates when no agent_name."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "ns", "key": "k", "value": "v", "accessCount": 1},
        ]

        data_store_service.get_all("user-123", "ns")

        mock_db.save.assert_not_called()

    def test_get_all_access_tracking_is_best_effort(self, data_store_service, mock_db):
        """Test get_all still returns data if access tracking save fails."""
        mock_db.list_all.return_value = [
            {
                "_id": "doc-1",
                "userId": "user-123",
                "namespace": "ns",
                "key": "k1",
                "value": "v1",
                "accessCount": 0,
            },
        ]
        mock_db.save.side_effect = Exception("DB write failed")

        result = data_store_service.get_all("user-123", "ns", agent_name="reader")

        assert result == {"k1": "v1"}

    def test_get_all_isolates_users(self, data_store_service, mock_db):
        """Test get_all only returns data for the specified user."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "shared", "key": "mine", "value": "yes"},
            {"userId": "user-456", "namespace": "shared", "key": "theirs", "value": "no"},
        ]

        result = data_store_service.get_all("user-123", "shared")

        assert result == {"mine": "yes"}


# =============================================================================
# Auto-Index Tests
# =============================================================================

class TestAutoIndexing:
    """Tests for automatic index creation."""

    def test_standard_indexes_created_on_init(self, mock_db):
        """Test that DataStoreService.__init__ calls ensure_index for standard indexes."""
        service = DataStoreService(mock_db)

        expected_calls = [
            call(DATA_STORE_DB, fields, index_name=name)
            for fields, name in _STANDARD_INDEXES
        ]
        mock_db.ensure_index.assert_has_calls(expected_calls)

    def test_standard_index_failure_is_nonfatal(self, mock_db):
        """Test that index creation failure at init doesn't crash the service."""
        mock_db.ensure_index.side_effect = Exception("CouchDB unreachable")

        service = DataStoreService(mock_db)
        assert service.db is mock_db

    def test_set_ensures_namespace_indexed(self, data_store_service, mock_db):
        """Test that set() triggers _ensure_namespace_indexed on first write."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        mock_db.ensure_index.reset_mock()

        data_store_service.set("user-123", "new-ns", "key", "value")

        assert mock_db.ensure_index.call_count >= 1

    def test_set_does_not_re_ensure_same_namespace(self, data_store_service, mock_db):
        """Test that repeated writes to same namespace don't re-call ensure_index."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        mock_db.ensure_index.reset_mock()

        data_store_service.set("user-123", "ns-x", "key1", "v1")
        data_store_service.set("user-123", "ns-x", "key2", "v2")
        data_store_service.set("user-123", "ns-x", "key3", "v3")

        # Only the first write triggers ensure_index
        assert mock_db.ensure_index.call_count == len(_STANDARD_INDEXES)

    def test_different_namespaces_each_trigger_ensure(self, data_store_service, mock_db):
        """Test that different namespaces each get their own ensure_index."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        mock_db.ensure_index.reset_mock()

        data_store_service.set("user-123", "ns-a", "key", "v")
        data_store_service.set("user-123", "ns-b", "key", "v")

        assert mock_db.ensure_index.call_count == 2 * len(_STANDARD_INDEXES)

    def test_indexed_namespaces_cache_is_per_user(self, data_store_service, mock_db):
        """Test that namespace index tracking is per-user."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        mock_db.ensure_index.reset_mock()

        data_store_service.set("user-a", "shared", "key", "v")
        data_store_service.set("user-b", "shared", "key", "v")

        assert mock_db.ensure_index.call_count == 2 * len(_STANDARD_INDEXES)

    def test_ensure_namespace_indexed_is_idempotent(self, data_store_service, mock_db):
        """Test that _ensure_namespace_indexed is a no-op after first call."""
        mock_db.ensure_index.reset_mock()

        data_store_service._ensure_namespace_indexed("user-123", "test-ns")
        data_store_service._ensure_namespace_indexed("user-123", "test-ns")
        data_store_service._ensure_namespace_indexed("user-123", "test-ns")

        assert mock_db.ensure_index.call_count == len(_STANDARD_INDEXES)


# =============================================================================
# AgentDataStoreProxy Tests
# =============================================================================

class TestAgentDataStoreProxy:
    """Tests for AgentDataStoreProxy class."""

    def test_use_namespace_returns_new_proxy(self, agent_proxy):
        """Test that use_namespace returns a new proxy with different namespace."""
        new_proxy = agent_proxy.use_namespace("custom-ns")
        
        assert new_proxy is not agent_proxy
        assert new_proxy._namespace == "custom-ns"
        assert new_proxy._user_id == agent_proxy._user_id
        assert new_proxy._agent_name == agent_proxy._agent_name

    def test_get_delegates_to_service(self, agent_proxy, mock_db):
        """Test that get() delegates to service with correct params."""
        mock_db.get.return_value = {"value": "test-value"}
        
        result = agent_proxy.get("my-key")
        
        assert result == "test-value"

    def test_get_with_default(self, agent_proxy, mock_db):
        """Test that get() returns default when key not found."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        
        result = agent_proxy.get("missing", default="fallback")
        
        assert result == "fallback"

    def test_set_delegates_to_service(self, agent_proxy, mock_db):
        """Test that set() delegates to service."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        
        agent_proxy.set("my-key", {"data": "value"})
        
        mock_db.save.assert_called_once()

    def test_delete_delegates_to_service(self, agent_proxy, mock_db):
        """Test that delete() delegates to service."""
        mock_db.delete.return_value = None
        
        result = agent_proxy.delete("my-key")
        
        assert result is True

    def test_list_keys_delegates_to_service(self, agent_proxy, mock_db):
        """Test that list_keys() delegates to service."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "key-1"},
            {"userId": "user-123", "namespace": "default", "key": "key-2"},
        ]
        
        result = agent_proxy.list_keys()
        
        assert result == ["key-1", "key-2"]

    def test_list_namespaces_delegates_to_service(self, agent_proxy, mock_db):
        """Test that list_namespaces() delegates to service."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "ns-a", "key": "key-1"},
            {"userId": "user-123", "namespace": "ns-b", "key": "key-2"},
        ]
        
        result = agent_proxy.list_namespaces()
        
        assert result == ["ns-a", "ns-b"]

    def test_get_all_delegates_to_service(self, agent_proxy, mock_db):
        """Test that get_all() delegates to service."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "k1", "value": "v1"},
            {"userId": "user-123", "namespace": "default", "key": "k2", "value": "v2"},
        ]

        result = agent_proxy.get_all()

        assert result == {"k1": "v1", "k2": "v2"}

    def test_get_all_uses_proxy_namespace(self, agent_proxy, mock_db):
        """Test that get_all() respects the proxy's namespace."""
        custom = agent_proxy.use_namespace("custom-ns")
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "custom-ns", "key": "k", "value": "v"},
            {"userId": "user-123", "namespace": "default", "key": "other", "value": "skip"},
        ]

        result = custom.get_all()

        assert result == {"k": "v"}

    def test_get_all_passes_agent_name(self, agent_proxy, mock_db):
        """Test that get_all() passes the proxy's agent_name for access tracking."""
        mock_db.list_all.return_value = [
            {
                "_id": "d1",
                "userId": "user-123",
                "namespace": "default",
                "key": "k",
                "value": "v",
                "accessCount": 0,
            },
        ]
        mock_db.save.return_value = {"rev": "2-abc"}

        agent_proxy.get_all()

        mock_db.save.assert_called_once()
        saved = mock_db.save.call_args[0][2]
        assert saved["lastAccessedByAgent"] == "test-agent"

    def test_get_many_delegates_to_service(self, agent_proxy, mock_db):
        """Test that get_many() delegates to service."""
        key_1_b64 = base64.urlsafe_b64encode(b"key-1").decode()
        
        def mock_get(db_name, doc_id):
            if key_1_b64 in doc_id:
                return {"value": "val-1"}
            raise HTTPException(status_code=404)
        
        mock_db.get.side_effect = mock_get
        
        result = agent_proxy.get_many(["key-1", "key-2"])
        
        assert result == {"key-1": "val-1"}

    def test_set_many_delegates_to_service(self, agent_proxy, mock_db):
        """Test that set_many() delegates to service."""
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        
        count = agent_proxy.set_many({"key-1": "val-1", "key-2": "val-2"})
        
        assert count == 2

    def test_clear_delegates_to_service(self, agent_proxy, mock_db):
        """Test that clear() delegates to service."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "default", "key": "key-1"},
        ]
        mock_db.delete.return_value = None
        
        count = agent_proxy.clear()
        
        assert count == 1


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunction:
    """Tests for get_data_store_service factory function."""

    def test_get_data_store_service(self, mock_db):
        """Test factory function creates service correctly."""
        service = get_data_store_service(mock_db)
        
        assert isinstance(service, DataStoreService)
        assert service.db is mock_db

    def test_factory_triggers_index_creation(self, mock_db):
        """Test that factory-created service eagerly creates indexes."""
        service = get_data_store_service(mock_db)

        mock_db.ensure_index.assert_called()


# =============================================================================
# Integration-style Tests (still using mocks but testing workflows)
# =============================================================================

class TestDataStoreWorkflows:
    """Test common data store workflows."""

    def test_namespace_discovery_workflow(self, data_store_service, mock_db):
        """Test discovering and querying namespaces."""
        mock_db.list_all.return_value = [
            {"userId": "user-123", "namespace": "files:repo-x", "key": "src/main.py"},
            {"userId": "user-123", "namespace": "files:repo-x", "key": "src/utils.py"},
            {"userId": "user-123", "namespace": "summary:repo-x", "key": "src/main.py"},
        ]
        
        namespaces = data_store_service.list_namespaces("user-123")
        assert "files:repo-x" in namespaces
        assert "summary:repo-x" in namespaces
        
        keys = data_store_service.list_keys("user-123", "files:repo-x")
        assert len(keys) == 2

    def test_cross_agent_data_sharing(self, mock_db):
        """Test that different agents can share data via same user_id."""
        service = DataStoreService(mock_db)
        
        proxy_a = AgentDataStoreProxy(service, "user-123", "agent-a", "shared")
        mock_db.get.side_effect = HTTPException(status_code=404)
        mock_db.save.return_value = {"rev": "1-abc"}
        
        proxy_a.set("report", {"data": "from-agent-a"})
        
        mock_db.get.side_effect = None
        mock_db.get.return_value = {"value": {"data": "from-agent-a"}}
        
        proxy_b = AgentDataStoreProxy(service, "user-123", "agent-b", "shared")
        result = proxy_b.get("report")
        assert result == {"data": "from-agent-a"}

    def test_user_isolation(self, data_store_service, mock_db):
        """Test that users cannot see each other's data."""
        mock_db.list_all.return_value = [
            {"userId": "user-a", "namespace": "default", "key": "secret-a"},
            {"userId": "user-b", "namespace": "default", "key": "secret-b"},
        ]
        
        keys_a = data_store_service.list_keys("user-a", "default")
        assert keys_a == ["secret-a"]
        
        keys_b = data_store_service.list_keys("user-b", "default")
        assert keys_b == ["secret-b"]
        
        ns_a = data_store_service.list_namespaces("user-a")
        ns_b = data_store_service.list_namespaces("user-b")
        assert ns_a == ["default"]
        assert ns_b == ["default"]

    def test_get_all_replaces_n_plus_1_pattern(self, data_store_service, mock_db):
        """Test that get_all eliminates the list_keys + get-per-key pattern.

        Core optimization: one find() call instead of 1 + N.
        """
        mock_db.list_all.return_value = [
            {"userId": "u", "namespace": "files:repo", "key": f"file-{i}", "value": f"content-{i}"}
            for i in range(100)
        ]

        result = data_store_service.get_all("u", "files:repo")

        assert mock_db.find.call_count == 1
        assert len(result) == 100
        assert result["file-0"] == "content-0"
        assert result["file-99"] == "content-99"

    def test_get_all_via_proxy_workflow(self, mock_db):
        """Test the full proxy workflow: use_namespace then get_all."""
        mock_db.list_all.return_value = [
            {"userId": "u1", "namespace": "files:myrepo", "key": "a.py", "value": "code-a"},
            {"userId": "u1", "namespace": "files:myrepo", "key": "b.py", "value": "code-b"},
            {"userId": "u1", "namespace": "summary:myrepo", "key": "a.py", "value": "summary-a"},
        ]

        service = DataStoreService(mock_db)
        proxy = AgentDataStoreProxy(service, "u1", "my-agent", "default")

        files = proxy.use_namespace("files:myrepo").get_all()
        summaries = proxy.use_namespace("summary:myrepo").get_all()

        assert files == {"a.py": "code-a", "b.py": "code-b"}
        assert summaries == {"a.py": "summary-a"}