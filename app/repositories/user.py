from typing import Annotated

import bcrypt
from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.engine import get_db
from app.models.user import User
from app.repositories.exception import (
    UserCreationException,
    UserAuthenticationException,
)
from app.schemas.user import UserCreate, UserRead, UserAuthenticate


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user: UserCreate) -> UserRead:
        try:
            hashed_password = bcrypt.hashpw(
                user.password.encode("utf-8"), bcrypt.gensalt()
            )
            new_user = User(email=user.email, password=hashed_password.decode("utf-8"))

            self.session.add(new_user)
            self.session.commit()
            self.session.refresh(new_user)
            return UserRead.model_validate(new_user)
        except IntegrityError:
            self.session.rollback()
            raise UserCreationException("This email already exists.")

    def authenticate(self, user: UserAuthenticate) -> UserRead:
        found_user = self.session.query(User).filter(User.email == user.email).first()

        if not found_user or not bcrypt.checkpw(
            user.password.encode("utf-8"), found_user.password.encode("utf-8")
        ):
            raise UserAuthenticationException("Incorrect email or password")

        return UserRead.model_validate(found_user)

    def check_api_key(self, api_key: str) -> UserRead | None:
        return self.session.query(User).filter(User.api_key == api_key).first()


async def get_user_repository(
    session: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    return UserRepository(session)
