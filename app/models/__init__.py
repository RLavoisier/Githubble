from app.db.engine import Base, engine
from app.models.user import User

__all__ = ["User"]


def init_db():
    Base.metadata.create_all(engine)
