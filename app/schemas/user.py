import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    password: str


class UserAuthenticate(UserCreate):
    pass


class UserRead(UserBase):
    id: uuid.UUID
    api_key: str
