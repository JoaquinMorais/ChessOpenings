import os

import psycopg2
from psycopg2 import sql as psycopg_sql
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, SQLModel
from fastapi.testclient import TestClient

_base_url = make_url(os.environ["DATABASE_URL"])
_base_database = _base_url.database or "chess"
test_database = (
    _base_database if _base_database.endswith("_test") else f"{_base_database}_test"
)

connection = psycopg2.connect(
    host=_base_url.host,
    port=_base_url.port or 5432,
    user=_base_url.username,
    password=_base_url.password,
    dbname="postgres",
)
connection.autocommit = True
try:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (test_database,)
        )
        if cursor.fetchone() is None:
            cursor.execute(
                psycopg_sql.SQL("CREATE DATABASE {}").format(
                    psycopg_sql.Identifier(test_database)
                )
            )
finally:
    connection.close()

os.environ["DATABASE_URL"] = _base_url.set(
    database=test_database
).render_as_string(hide_password=False)

import pytest

from config.database import engine
from index import app

import models.node  # noqa: F401
import models.opening  # noqa: F401
import models.seed_import  # noqa: F401
import models.training  # noqa: F401

if not test_database.endswith("_test"):
    raise RuntimeError(
        "Los tests deben ejecutarse contra una base de pruebas terminada en _test."
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