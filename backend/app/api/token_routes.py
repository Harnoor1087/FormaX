from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field

from ..security.api_auth import ApiRole, require_roles
from ..storage.token_store import token_store

router = APIRouter(prefix="/v1/tokens", tags=["Token Management"])


class CreateTokenRequest(BaseModel):
    token_name: str = Field(..., min_length=1, max_length=100, description="Human-readable token name")
    role: str = Field(..., description="Token role: operator or reviewer")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="Token expiration in days")
    created_by: Optional[str] = Field(None, description="Creator identifier")


class CreateTokenResponse(BaseModel):
    token_id: str
    token_value: str
    token_name: str
    role: str
    created_at: str
    expires_at: Optional[str]
    warning: str = "Store this token securely. It will not be shown again."


class TokenInfo(BaseModel):
    token_id: str
    token_name: str
    role: str
    created_by: Optional[str]
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str]
    is_active: bool


class TokenUsageLog(BaseModel):
    endpoint: str
    client_ip: Optional[str]
    used_at: str


@router.post("", response_model=CreateTokenResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    request: CreateTokenRequest,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    """
    Create a new API token (reviewer role only).
    The token value is shown only once during creation.
    """
    if request.role not in ("operator", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'operator' or 'reviewer'.",
        )
    
    try:
        token_data = token_store.generate_token(
            token_name=request.token_name,
            role=request.role,
            created_by=request.created_by,
            expires_in_days=request.expires_in_days,
        )
        
        return CreateTokenResponse(
            token_id=token_data["token_id"],
            token_value=token_data["token_value"],
            token_name=token_data["token_name"],
            role=token_data["role"],
            created_at=token_data["created_at"],
            expires_at=token_data["expires_at"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[TokenInfo])
def list_tokens(
    include_inactive: bool = Query(False, description="Include revoked tokens"),
    role: Optional[str] = Query(None, description="Filter by role"),
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    """
    List all API tokens (reviewer role only).
    Token values are never exposed in list endpoints.
    """
    if role and role not in ("operator", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role filter must be 'operator' or 'reviewer'.",
        )
    
    tokens = token_store.list_tokens(
        include_inactive=include_inactive,
        role=role,
    )
    
    return [TokenInfo(**token) for token in tokens]


@router.get("/{token_id}", response_model=TokenInfo)
def get_token(
    token_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    """
    Get details for a specific token (reviewer role only).
    Token value is never exposed after creation.
    """
    token = token_store.get_token(token_id)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found.",
        )
    
    return TokenInfo(**token)


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: str,
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    """
    Revoke (deactivate) a token (reviewer role only).
    Revoked tokens can no longer be used for authentication.
    """
    success = token_store.revoke_token(token_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found.",
        )


@router.get("/{token_id}/usage", response_model=list[TokenUsageLog])
def get_token_usage(
    token_id: str,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    auth: tuple[ApiRole, Optional[str]] = Depends(require_roles("reviewer")),
):
    """
    Get usage statistics for a specific token (reviewer role only).
    Returns recent usage logs with endpoint and client IP.
    """
    token = token_store.get_token(token_id)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found.",
        )
    
    usage_logs = token_store.get_token_usage_stats(token_id, limit=limit)
    return [TokenUsageLog(**log) for log in usage_logs]

