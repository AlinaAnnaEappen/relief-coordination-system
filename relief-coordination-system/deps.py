# deps.py (Owner: Member A)
# Login helpers and role verification dependencies

from fastapi import Request, HTTPException, status, Depends
from itsdangerous import URLSafeSerializer, BadSignature
import config

# Serializer for decoding session cookies (used in full auth mode)
serializer = URLSafeSerializer(config.SECRET_KEY, salt="session")

def get_current_user(request: Request):
    """
    Returns the currently logged-in user dictionary:
    {user_id, username, full_name, role, camp_id, hub_id, district}

    If DEV_BYPASS_LOGIN is true in config, returns a mock user based on
    DEV_FAKE_ROLE, DEV_FAKE_CAMP_ID, and DEV_FAKE_HUB_ID so teammates are not blocked.
    """
    if config.DEV_BYPASS_LOGIN:
        return {
            "user_id": 1,
            "username": f"dev_{config.DEV_FAKE_ROLE}",
            "full_name": f"Dev {config.DEV_FAKE_ROLE.replace('_', ' ').title()}",
            "role": config.DEV_FAKE_ROLE,
            "camp_id": config.DEV_FAKE_CAMP_ID,
            "hub_id": config.DEV_FAKE_HUB_ID,
            "district": "Alappuzha",
        }

    # Check for session cookie named "session_user"
    cookie_value = request.cookies.get("session_user")
    if not cookie_value:
        return None

    try:
        user_data = serializer.loads(cookie_value)
        return user_data
    except BadSignature:
        return None

def require_role(*roles: str):
    """
    Dependency factory to enforce role-based access control.
    Usage:
        user = Depends(require_role("admin"))
        user = Depends(require_role("admin", "camp_officer"))
    """
    def role_checker(current_user: dict = Depends(get_current_user)):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if roles and current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: this action requires one of the following roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker
