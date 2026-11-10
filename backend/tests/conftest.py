from sqlalchemy import text
from sqlmodel import Session, SQLModel
from fastapi.testclient import TestClient

import pytest

from config.database import engine
from config.settings import settings
from index import app

import models.node  # noqa: F401
import models.opening  # noqa: F401
import models.training  # noqa: F401

if "chess_test" not in settings.database_url:
    raise RuntimeError(
        "Los tests deben ejecutarse contra la base de pruebas chess_test. "
        "Usa: docker compose run --rm backend-test"
    )


@pytest.fixture(scope="session", autouse=True)
def _schema():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    table_names = ", ".join(table.name for table in SQLModel.metadata.sorted_tables)
    with Session(engine) as session:
        session.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )
        session.commit()


@pytest.fixture(scope="session")
def client():
    test_client = TestClient(app)
    yield test_client
    test_client.close()


@pytest.fixture
def session():
    with Session(engine) as db_session:
        yield db_session