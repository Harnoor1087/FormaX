import secrets
from typing import FrozenSet, Literal, cast

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import settings

ApiRole = Literal["operator", "reviewer"]
bearer_scheme = HTTPBearer(auto_error=False)


def require_roles(*allowed_roles: ApiRole):
    allowed: FrozenSet[str] = frozenset(allowed_roles)

    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> ApiRole:
        operator_token = settings.OPERATOR_API_TOKEN
        reviewer_token = settings.REVIEWER_API_TOKEN
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
        if operator_token and secrets.compare_digest(token, operator_token):
            role = "operator"
        elif reviewer_token and secrets.compare_digest(token, reviewer_token):
            role = "reviewer"

        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The bearer access token is invalid.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This access token does not have permission for this action.",
            )
        return cast(ApiRole, role)

    return dependency
