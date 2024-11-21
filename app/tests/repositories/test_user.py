import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError
import uuid
from app.models.user import User
from app.repositories.exception import (
    UserCreationException,
    UserAuthenticationException,
)
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserRead, UserAuthenticate


@pytest.fixture
def mocked_session():
    return MagicMock()


@pytest.fixture
def repository(mocked_session):
    return UserRepository(mocked_session)


class TestUserRepository:
    def test_create_valid_user(self, repository, mocked_session):
        user_input = UserCreate(email="user@example.com", password="secure_password")
        hashed_password = b"$2b$12$hashedpassword"
        new_user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            password=hashed_password.decode(),
            api_key="test_api_key",
        )

        def mock_refresh(user):
            setattr(user, "id", new_user.id)
            setattr(user, "api_key", new_user.api_key)

        with patch("bcrypt.hashpw", return_value=hashed_password):
            mocked_session.refresh.side_effect = mock_refresh

            result = repository.create(user_input)

            mocked_session.add.assert_called_once()
            mocked_session.commit.assert_called_once()
            mocked_session.refresh.assert_called_once()
            assert result.email == "user@example.com"
            assert result.api_key == "test_api_key"
            assert isinstance(result, UserRead)

    def test_create_user_with_conflict(self, repository, mocked_session):
        user_input = UserCreate(email="user@example.com", password="secure_password")
        mocked_session.add.side_effect = IntegrityError(
            "Integrity constraint", {}, None
        )

        with pytest.raises(UserCreationException) as exc_info:
            repository.create(user_input)

        mocked_session.rollback.assert_called_once()
        assert "This email already exists." in str(exc_info.value)

    def test_authenticate_valid_user(self, repository, mocked_session):
        user_input = UserAuthenticate(
            email="user@example.com", password="secure_password"
        )
        hashed_password = b"$2b$12$hashedpassword"
        found_user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            password=hashed_password.decode(),
            api_key="test_api_key",
        )

        with patch("bcrypt.checkpw", return_value=True):
            mocked_session.query.return_value.filter.return_value.first.return_value = (
                found_user
            )

            result = repository.authenticate(user_input)

            mocked_session.query.assert_called_once()
            assert result.email == "user@example.com"
            assert result.api_key == "test_api_key"
            assert isinstance(result, UserRead)

    def test_authenticate_invalid_user(self, repository, mocked_session):
        user_input = UserAuthenticate(
            email="user@example.com", password="wrong_password"
        )
        mocked_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(UserAuthenticationException) as exc_info:
            repository.authenticate(user_input)

        assert "Incorrect email or password" in str(exc_info.value)

    def test_check_valid_api_key(self, repository, mocked_session):
        valid_api_key = "valid_api_key"
        user = User(id=uuid.uuid4(), email="user@example.com", api_key=valid_api_key)

        mocked_session.query.return_value.filter.return_value.first.return_value = user

        result = repository.check_api_key(valid_api_key)

        mocked_session.query.assert_called_once()
        assert result.email == "user@example.com"
        assert result.api_key == valid_api_key

    def test_check_invalid_api_key(self, repository, mocked_session):
        invalid_api_key = "invalid_api_key"
        mocked_session.query.return_value.filter.return_value.first.return_value = None

        result = repository.check_api_key(invalid_api_key)

        mocked_session.query.assert_called_once()
        assert result is None
