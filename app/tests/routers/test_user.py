import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException
from app.models import User
from app.repositories.exception import (
    UserCreationException,
    UserAuthenticationException,
)
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserRead, UserAuthenticate
from app.routers.user import validate_api_key, create_user, authenticate

# Mocked Data
MOCK_USER = User(
    id="123e4567-e89b-12d3-a456-426614174000",
    email="test@example.com",
    api_key="test_api_key",
)

MOCK_USER_READ = UserRead(
    id="123e4567-e89b-12d3-a456-426614174000",
    email="test@example.com",
    api_key="test_api_key",
)

MOCK_USER_CREATE = UserCreate(email="test@example.com", password="secure_password")
MOCK_USER_AUTHENTICATE = UserAuthenticate(
    email="test@example.com", password="secure_password"
)


# Fixtures
@pytest.fixture
def mock_user_repository():
    repository = AsyncMock(spec=UserRepository)
    repository.check_api_key.return_value = MOCK_USER
    repository.create.return_value = MOCK_USER_READ
    repository.authenticate.return_value = MOCK_USER_READ
    return repository


@pytest.fixture
def mock_invalid_user_repository():
    repository = AsyncMock(spec=UserRepository)
    repository.check_api_key.return_value = None
    repository.create.side_effect = UserCreationException("This email already exists.")
    repository.authenticate.side_effect = UserAuthenticationException(
        "Invalid email or password."
    )
    return repository


# Test Suite
class TestUserRoutes:
    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, mock_user_repository):
        user = await validate_api_key(
            api_key="test_api_key", user_repository=mock_user_repository
        )
        assert user.email == MOCK_USER.email
        assert user.api_key == MOCK_USER.api_key

    @pytest.mark.asyncio
    async def test_validate_api_key_failure(self, mock_invalid_user_repository):
        with pytest.raises(HTTPException) as exc_info:
            await validate_api_key(
                api_key="invalid_key", user_repository=mock_invalid_user_repository
            )
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Missing or invalid API key"

    @pytest.mark.asyncio
    async def test_create_user_success(self, mock_user_repository):
        result = await create_user(
            user=MOCK_USER_CREATE, user_repository=mock_user_repository
        )
        assert result.email == MOCK_USER_READ.email
        assert result.api_key == MOCK_USER_READ.api_key

    @pytest.mark.asyncio
    async def test_create_user_conflict(self, mock_invalid_user_repository):
        with pytest.raises(HTTPException) as exc_info:
            await create_user(
                user=MOCK_USER_CREATE, user_repository=mock_invalid_user_repository
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"] == "This email already exists."

    @pytest.mark.asyncio
    async def test_authenticate_success(self, mock_user_repository):
        result = await authenticate(
            user=MOCK_USER_AUTHENTICATE, user_repository=mock_user_repository
        )
        assert result.email == MOCK_USER_READ.email
        assert result.api_key == MOCK_USER_READ.api_key

    @pytest.mark.asyncio
    async def test_authenticate_failure(self, mock_invalid_user_repository):
        with pytest.raises(HTTPException) as exc_info:
            await authenticate(
                user=MOCK_USER_AUTHENTICATE,
                user_repository=mock_invalid_user_repository,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error"] == "Invalid email or password."
