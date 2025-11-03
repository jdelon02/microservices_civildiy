"""
Shared JWT validation utilities for microservices.
Each service uses this to validate tokens created by auth-service.
"""

import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header
import jwt

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises HTTPException if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and validate JWT from Authorization header.
    Use this in route dependencies to protect endpoints.
    
    Example:
        @app.get("/api/posts")
        async def get_posts(current_user: Dict = Depends(get_current_user)):
            user_id = current_user["sub"]
            # ... process request
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authorization header"
        )
    
    try:
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization format"
            )
        
        token = parts[1]
        payload = decode_token(token)
        return payload
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed"
        )


def get_user_id_from_token(token: str) -> str:
    """Extract user_id (sub claim) from token"""
    payload = decode_token(token)
    return payload.get("sub")


def get_email_from_token(token: str) -> str:
    """Extract email from token"""
    payload = decode_token(token)
    return payload.get("email")
