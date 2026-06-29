"""Tests for MCP servers."""

import pytest
from backend.security.auth import auth_manager
from backend.security.encryption import encrypt_data, decrypt_data
from backend.security.audit import audit_logger


class TestAuthManager:
    """Test authentication and JWT token management."""

    def test_hash_password(self):
        password = "test_password_123"
        hashed = auth_manager.hash_password(password)
        assert hashed != password
        assert auth_manager.verify_password(password, hashed)

    def test_verify_wrong_password(self):
        hashed = auth_manager.hash_password("correct_password")
        assert not auth_manager.verify_password("wrong_password", hashed)

    def test_create_and_verify_token(self):
        token = auth_manager.create_access_token("user_123", {"role": "admin"})
        payload = auth_manager.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user_123"
        assert payload["role"] == "admin"

    def test_verify_invalid_token(self):
        payload = auth_manager.verify_token("invalid.token.here")
        assert payload is None

    def test_get_user_id_from_token(self):
        token = auth_manager.create_access_token("user_456")
        user_id = auth_manager.get_user_id_from_token(token)
        assert user_id == "user_456"

    def test_get_user_id_from_invalid_token(self):
        user_id = auth_manager.get_user_id_from_token("bad_token")
        assert user_id is None


class TestEncryption:
    """Test data encryption and decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        original = "sensitive_api_key_12345"
        encrypted = encrypt_data(original)
        assert encrypted != original
        decrypted = decrypt_data(encrypted)
        assert decrypted == original

    def test_different_encryptions_are_different(self):
        encrypted1 = encrypt_data("data1")
        encrypted2 = encrypt_data("data2")
        assert encrypted1 != encrypted2

    def test_encrypt_empty_string(self):
        encrypted = encrypt_data("")
        decrypted = decrypt_data(encrypted)
        assert decrypted == ""


class TestAuditLogger:
    """Test audit logging."""

    def test_log_action(self):
        initial_count = len(audit_logger.logs)
        audit_logger.log_action(
            user_id="test_user",
            action="test_action",
            tool_name="test_tool",
            tool_args={"key": "value", "access_token": "secret123"},
            result={"status": "ok"},
        )
        assert len(audit_logger.logs) == initial_count + 1
        last_log = audit_logger.logs[-1]
        assert last_log["user_id"] == "test_user"
        assert last_log["action"] == "test_action"
        # Sensitive data should be sanitized
        assert last_log["arguments"]["access_token"] == "***"

    def test_log_auth_event(self):
        initial_count = len(audit_logger.logs)
        audit_logger.log_auth_event("user_1", "login")
        assert len(audit_logger.logs) == initial_count + 1

    def test_get_user_logs(self):
        audit_logger.log_action(
            user_id="filter_test_user",
            action="action1",
            tool_name="tool1",
            tool_args={},
            result={},
        )
        audit_logger.log_action(
            user_id="other_user",
            action="action2",
            tool_name="tool2",
            tool_args={},
            result={},
        )
        user_logs = audit_logger.get_user_logs("filter_test_user")
        assert all(log["user_id"] == "filter_test_user" for log in user_logs)
