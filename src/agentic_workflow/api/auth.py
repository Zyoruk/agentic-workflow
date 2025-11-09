"""
JWT Authentication for Agentic Workflow API.

This module provides JWT-based authentication for securing API endpoints.
Sprint 1-2: Security Implementation
"""

from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

# JWT Configuration
SECRET_KEY = "agentic-workflow-secret-key-change-in-production"  # TODO: Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
security = HTTPBearer()


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    scopes: list[str] = []


# In-memory user store (for MVP - will move to database in Sprint 3-4)
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@agenticworkflow.com",
        "full_name": "Admin User",
        "disabled": False,
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "scopes": ["workflow:read", "workflow:write", "workflow:execute", "workflow:delete"],
    },
    "user": {
        "username": "user",
        "email": "user@agenticworkflow.com",
        "full_name": "Regular User",
        "disabled": False,
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "scopes": ["workflow:read", "workflow:execute"],
    },
}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        TokenData with username and scopes
        
    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
    except JWTError as e:
        logger.error(f"JWT verification error: {e}")
        raise credentials_exception
    
    return token_data


def get_user(username: str) -> Optional[User]:
    """
    Get user from the database.
    
    Args:
        username: Username to lookup
        
    Returns:
        User object if found, None otherwise
    """
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return User(**user_dict)
    return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = verify_token(token)
    user = get_user(username=token_data.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user.
    
    Args:
        current_user: Current user from authentication
        
    Returns:
        Active user
        
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_scope(required_scope: str):
    """
    Dependency to require a specific scope.
    
    Args:
        required_scope: Required scope for the endpoint
        
    Returns:
        Dependency function
    """
    async def scope_dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if required_scope not in current_user.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires '{required_scope}' scope"
            )
        return current_user
    
    return scope_dependency


# Convenience dependencies for common scopes
require_workflow_read = require_scope("workflow:read")
require_workflow_write = require_scope("workflow:write")
require_workflow_execute = require_scope("workflow:execute")
require_workflow_delete = require_scope("workflow:delete")
