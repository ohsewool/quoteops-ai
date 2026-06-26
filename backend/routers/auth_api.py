from fastapi import APIRouter, Header, HTTPException, Request

from backend.db import get_connection
from backend.schemas.auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutResponse,
    AdminPublic,
)
from backend.services.auth_service import (
    AuthError,
    get_admin_from_token,
    login_admin,
    logout_admin,
    require_role,
)
from backend.services.audit_logger import audit_actor, log_audit_event

router = APIRouter(prefix="/api/auth", tags=["auth"])


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization bearer token is required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authorization bearer token is required.")
    return token.strip()


def current_admin_from_authorization(authorization: str | None) -> dict:
    token = extract_bearer_token(authorization)
    try:
        with get_connection() as connection:
            return get_admin_from_token(connection, token=token)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def require_admin_roles(
    authorization: str | None,
    allowed_roles: set[str],
    *,
    request: Request | None = None,
    action: str = "protected_admin_operation",
) -> dict:
    admin = current_admin_from_authorization(authorization)
    try:
        require_role(admin, allowed_roles)
    except AuthError as exc:
        with get_connection() as connection:
            log_audit_event(
                connection,
                action="role_restricted_action_blocked",
                entity_type="admin_permission",
                entity_id=admin["id"],
                entity_label=admin["email"],
                metadata={
                    "attempted_action": action,
                    "allowed_roles": sorted(allowed_roles),
                    "admin_role": admin["role"],
                    "path": str(request.url.path) if request else None,
                    "method": request.method if request else None,
                },
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                **audit_actor(admin),
            )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return admin


def require_owner_admin(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    return require_admin_roles(
        authorization,
        {"owner"},
        request=request,
        action=f"{request.method} {request.url.path}",
    )


def require_manager_or_owner_admin(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    return require_admin_roles(
        authorization,
        {"owner", "manager"},
        request=request,
        action=f"{request.method} {request.url.path}",
    )


@router.post("/login", response_model=AdminLoginResponse)
def login(request: AdminLoginRequest, http_request: Request) -> dict:
    try:
        with get_connection() as connection:
            result = login_admin(
                connection,
                email=request.email,
                password=request.password,
            )
            admin = result["admin"]
            log_audit_event(
                connection,
                action="admin_login",
                entity_type="admin_user",
                entity_id=admin["id"],
                entity_label=admin["email"],
                metadata={"email": admin["email"]},
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
                **audit_actor(admin),
            )
            return result
    except AuthError as exc:
        with get_connection() as connection:
            log_audit_event(
                connection,
                action="admin_login_failed",
                entity_type="admin_user",
                entity_label=request.email,
                metadata={"email": request.email},
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("user-agent"),
            )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/me", response_model=AdminPublic)
def me(authorization: str | None = Header(default=None)) -> dict:
    return current_admin_from_authorization(authorization)


@router.post("/logout", response_model=AdminLogoutResponse)
def logout(http_request: Request, authorization: str | None = Header(default=None)) -> dict:
    token = extract_bearer_token(authorization)
    with get_connection() as connection:
        admin = None
        try:
            admin = get_admin_from_token(connection, token=token)
        except AuthError:
            pass
        result = logout_admin(connection, token=token)
        log_audit_event(
            connection,
            action="admin_logout",
            entity_type="admin_user",
            entity_id=admin["id"] if admin else None,
            entity_label=admin["email"] if admin else None,
            ip_address=http_request.client.host if http_request.client else None,
            user_agent=http_request.headers.get("user-agent"),
            **audit_actor(admin),
        )
        return result
