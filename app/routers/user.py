from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends, Security
from fastapi.security import APIKeyHeader

from app.models import User
from app.repositories.exception import (
    UserCreationException,
    UserAuthenticationException,
)
from app.repositories.user import UserRepository, get_user_repository
from app.schemas.user import UserCreate, UserRead, UserAuthenticate

router = APIRouter(prefix="/user", tags=["user"])

api_key_header = APIKeyHeader(name="X-API-Key")


async def validate_api_key(
    api_key: str = Security(api_key_header),
    user_repository: UserRepository = Depends(get_user_repository),
) -> User:
    user = user_repository.check_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
    return user


@router.post(
    "/create_user",
    summary="Create a new api user.",
    description="Create a user using an email and a password. An Api Key will be automatically generated.",
)
async def create_user(
    user: UserCreate,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    try:
        return user_repository.create(user)
    except UserCreationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(e)}
        )


@router.post(
    "/authenticate",
    summary="Retrieve your API key upon authentication..",
    description="Authenticate your account with you email and password to retrieve you Api Key.",
)
async def authenticate(
    user: UserAuthenticate,
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserRead:
    try:
        return user_repository.authenticate(user)
    except UserAuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error": str(e)}
        )
