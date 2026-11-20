"""Tests for token management system."""
import pytest
from datetime import datetime, timedelta, timezone

from app.storage.token_store import TokenStore


@pytest.fixture
def token_store():
    """Create a temporary token store for testing."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    store = TokenStore(database_path=db_path)
    yield store
    
    # Cleanup
    import os
    os.unlink(db_path)


def test_generate_operator_token(token_store):
    """Test generating an operator token."""
    token = token_store.generate_token(
        token_name="Test Operator",
        role="operator",
    )
    
    assert token["token_id"]
    assert token["token_value"].startswith("ftx_")
    assert token["token_name"] == "Test Operator"
    assert token["role"] == "operator"
    assert token["created_at"]
    assert token["expires_at"] is None


def test_generate_reviewer_token_with_expiration(token_store):
    """Test generating a reviewer token with expiration."""
    token = token_store.generate_token(
        token_name="Test Reviewer",
        role="reviewer",
        expires_in_days=30,
    )
    
    assert token["role"] == "reviewer"
    assert token["expires_at"]
    
    # Verify expiration is approximately 30 days from now
    expires = datetime.fromisoformat(token["expires_at"])
    expected = datetime.now(timezone.utc) + timedelta(days=30)
    delta = abs((expires - expected).total_seconds())
    assert delta < 60  # Within 1 minute


def test_validate_active_token(token_store):
    """Test validating an active token."""
    created = token_store.generate_token(
        token_name="Valid Token",
        role="operator",
    )
    
    validated = token_store.validate_token(created["token_value"])
    
    assert validated is not None
    assert validated["token_id"] == created["token_id"]
    assert validated["role"] == "operator"


def test_validate_invalid_token(token_store):
    """Test validating an invalid token."""
    validated = token_store.validate_token("ftx_invalid_token")
    assert validated is None


def test_validate_revoked_token(token_store):
    """Test validating a revoked token."""
    created = token_store.generate_token(
        token_name="To Be Revoked",
        role="operator",
    )
    
    # Revoke the token
    token_store.revoke_token(created["token_id"])
    
    # Validation should fail
    validated = token_store.validate_token(created["token_value"])
    assert validated is None


def test_list_tokens(token_store):
    """Test listing tokens."""
    # Create multiple tokens
    token_store.generate_token("Token 1", "operator")
    token_store.generate_token("Token 2", "reviewer")
    token_store.generate_token("Token 3", "operator")
    
    tokens = token_store.list_tokens()
    assert len(tokens) == 3


def test_list_tokens_by_role(token_store):
    """Test filtering tokens by role."""
    token_store.generate_token("Operator 1", "operator")
    token_store.generate_token("Reviewer 1", "reviewer")
    token_store.generate_token("Operator 2", "operator")
    
    operators = token_store.list_tokens(role="operator")
    reviewers = token_store.list_tokens(role="reviewer")
    
    assert len(operators) == 2
    assert len(reviewers) == 1


def test_list_tokens_include_inactive(token_store):
    """Test listing tokens including revoked ones."""
    token1 = token_store.generate_token("Active", "operator")
    token2 = token_store.generate_token("Revoked", "operator")
    
    token_store.revoke_token(token2["token_id"])
    
    active_only = token_store.list_tokens(include_inactive=False)
    all_tokens = token_store.list_tokens(include_inactive=True)
    
    assert len(active_only) == 1
    assert len(all_tokens) == 2


def test_record_token_usage(token_store):
    """Test recording token usage."""
    token = token_store.generate_token("Test", "operator")
    
    # Record usage
    token_store.record_token_usage(
        token["token_id"],
        "/api/generate",
        "192.168.1.1",
    )
    
    # Get token details
    details = token_store.get_token(token["token_id"])
    assert details["last_used_at"] is not None


def test_get_token_usage_stats(token_store):
    """Test getting token usage statistics."""
    token = token_store.generate_token("Test", "operator")
    
    # Record multiple uses
    for i in range(5):
        token_store.record_token_usage(
            token["token_id"],
            f"/api/endpoint{i}",
            "192.168.1.1",
        )
    
    usage = token_store.get_token_usage_stats(token["token_id"])
    assert len(usage) == 5


def test_token_expiration_validation(token_store):
    """Test that expired tokens are not validated."""
    # Create token that expires in the past
    token = token_store.generate_token(
        token_name="Expired",
        role="operator",
        expires_in_days=-1,  # Expired yesterday
    )
    
    # Validation should fail
    validated = token_store.validate_token(token["token_value"])
    assert validated is None


def test_token_uniqueness(token_store):
    """Test that token values are unique."""
    token1 = token_store.generate_token("Token 1", "operator")
    token2 = token_store.generate_token("Token 2", "operator")
    
    assert token1["token_value"] != token2["token_value"]


def test_invalid_role_raises_error(token_store):
    """Test that invalid roles raise errors."""
    with pytest.raises(ValueError, match="Invalid role"):
        token_store.generate_token("Test", "invalid_role")

