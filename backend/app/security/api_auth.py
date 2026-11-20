import secrets
from typing import FrozenSet, Literal, Optional, cast

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings
from ..storage.token_store import token_store
from ..security.token_rate_limiter import token_rate_limiter

ApiRole = Literal["operator", "reviewer"]
bearer_scheme = HTTPBearer(auto_error=False)


def require_roles(*allowed_roles: ApiRole):
    allowed: FrozenSet[str] = frozenset(allowed_roles)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        request: Request = None,
    ) -> tuple[ApiRole, Optional[str]]:
        client_ip = request.client.host if request and request.client else "unknown"
        
        # Check rate limiting
        if token_rate_limiter.is_locked_out(client_ip):
            remaining = token_rate_limiter.get_lockout_remaining(client_ip)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed authentication attempts. Try again in {remaining} seconds.",
                headers={"Retry-After": str(remaining)},
            )
        
        operator_token = settings.OPERATOR_API_TOKEN
        reviewer_token = settings.REVIEWER_API_TOKEN
        
        # Fallback to legacy tokens if database is empty
        if not operator_token and not reviewer_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API authentication is not configured. Set OPERATOR_API_TOKEN and REVIEWER_API_TOKEN.",
            )
        
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A bearer access token is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        role = None
        token_id = None
        
        # First, try database tokens
        token_data = token_store.validate_token(token)
        if token_data:
            role = token_data["role"]
            token_id = token_data["token_id"]
            
            # Record successful attempt
            token_rate_limiter.record_attempt(client_ip, success=True)
            
            # Record usage
            endpoint = request.url.path if request else "unknown"
            token_store.record_token_usage(token_id, endpoint, client_ip)
        else:
            # Fallback to legacy static tokens
            if operator_token and secrets.compare_digest(token, operator_token):
                role = "operator"
                token_rate_limiter.record_attempt(client_ip, success=True)
            elif reviewer_token and secrets.compare_digest(token, reviewer_token):
                role = "reviewer"
                token_rate_limiter.record_attempt(client_ip, success=True)

        if role is None:
            # Record failed attempt
            token_rate_limiter.record_attempt(client_ip, success=False)
            
            attempts_remaining = token_rate_limiter.get_attempts_remaining(client_ip)
            detail = "The bearer access token is invalid."
            if attempts_remaining > 0:
                detail += f" {attempts_remaining} attempts remaining before temporary lockout."
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This access token does not have permission for this action.",
            )
        
        return cast(ApiRole, role), token_id

    return dependency
