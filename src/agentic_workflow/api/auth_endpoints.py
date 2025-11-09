"""
Authentication API endpoints.

Provides login and token management endpoints.
Sprint 1-2: Security Implementation
"""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from agentic_workflow.api.auth import (
    create_access_token,
    get_current_active_user,
    fake_users_db,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    User,
)
from agentic_workflow.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    For MVP, we use a simple comparison (passwords are "secret" for all users).
    In production, this would use proper password hashing (bcrypt, argon2, etc.)
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    # For MVP: accept "secret" as password for all users
    # TODO: Implement proper password hashing in Sprint 3-4
    return plain_password == "secret"


def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        User object if authentication successful, None otherwise
    """
    if username not in fake_users_db:
        return None
    
    user_dict = fake_users_db[username]
    if not verify_password(password, user_dict["hashed_password"]):
        return None
    
    return User(**user_dict)


@router.post("/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Login endpoint using OAuth2 password flow.
    
    Args:
        form_data: OAuth2 form data with username and password
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/json", response_model=Token)
async def login_json(login_data: LoginRequest):
    """
    Login endpoint using JSON request body.
    
    Args:
        login_data: Login credentials
        
    Returns:
        JWT access token
        
    Raises:
        HTTPException: If authentication fails
    """
    user = authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.username} logged in successfully")
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user details
    """
    return current_user
