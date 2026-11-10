from sqlmodel import SQLModel, Session, create_engine

from config.settings import settings

_database_url = settings.database_url

if _database_url.startswith("sqlite"):
    engine = create_engine(
        _database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(_database_url, echo=False)


def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)