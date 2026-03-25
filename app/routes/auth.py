from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService
from app.dependencies.auth_dependency import get_current_user
from app.models.user import User
from fastapi.security import OAuth2PasswordRequestForm # Add this import


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    """

    user = await AuthService.register_user(db=db, user_data=user_data)
    return user



@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    # Change credentials from UserLogin to OAuth2PasswordRequestForm
    credentials: OAuth2PasswordRequestForm = Depends(), # now JSON to Form body ( should have "username" and "password" fields )
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return JWT tokens.
    """
    # Note: OAuth2PasswordRequestForm uses .username instead of .email
    # We map it here so your AuthService doesn't have to change much
    login_data = UserLogin(email=credentials.username, password=credentials.password)
    
    tokens = await AuthService.login_user(db=db, credentials=login_data)
    return tokens


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user.
    """

    return current_user


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    """

    tokens = await AuthService.refresh_access_token(
        db=db,
        refresh_token=refresh_token,
    )

    return tokens