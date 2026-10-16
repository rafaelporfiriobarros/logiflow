import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def postgres_test_session_factory():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL não configurada.")

    url = make_url(database_url)

    if url.get_backend_name() != "postgresql":
        pytest.fail("Os testes de integração exigem PostgreSQL.")

    if url.database != "logiflow_test":
        pytest.fail("O banco permitido para testes é logiflow_test.")

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"hostaddr": "127.0.0.1"},
    )

    factory = sessionmaker(
        bind=engine,
        autoflush=True,
        expire_on_commit=False,
    )

    yield factory

    engine.dispose()
