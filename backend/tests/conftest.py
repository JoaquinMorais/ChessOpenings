import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from fastapi.testclient import TestClient

import pytest

from config.database import get_session
from index import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture
def client():
    SQLModel.metadata.create_all(engine)
    with TestClient(app) as test_client:
        yield test_client
    SQLModel.metadata.drop_all(engine)