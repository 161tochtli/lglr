from __future__ import annotations

import os
from collections.abc import Callable, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


# ---------------------------------------------------------------------------
# Fixtures para tests unitarios (in-memory, rápidos)
# ---------------------------------------------------------------------------

@pytest.fixture()
def app():  # type: ignore[no-untyped-def]
    """App limpia con persistencia in-memory (default para unit tests)."""
    return create_app(configure_logs=True, persistence="memory", run_worker=False)


@pytest.fixture()
def client(app) -> Generator[TestClient, None, None]:  # type: ignore[no-untyped-def]
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def app_factory() -> Callable[..., Any]:
    """
    Factory para crear apps limpias con overrides puntuales de infraestructura.

    Uso:
      app = app_factory(transaction_repo=FakeTxRepo(), idempotency_store=FakeStore())
    """

    def _factory(**overrides: Any):
        app = create_app(configure_logs=True, persistence="memory", run_worker=False)
        for key, value in overrides.items():
            setattr(app.state, key, value)
        return app

    return _factory


# ---------------------------------------------------------------------------
# Fixtures para tests de integración con SQLite
# ---------------------------------------------------------------------------

@pytest.fixture()
def sqlite_app(tmp_path):  # type: ignore[no-untyped-def]
    """App con SQLite file-backed (tests de integración sin Docker)."""
    db_path = str(tmp_path / "test.db")
    return create_app(configure_logs=False, persistence="sqlite", database_url=f"sqlite://{db_path}", run_worker=False)


@pytest.fixture()
def sqlite_client(sqlite_app) -> Generator[TestClient, None, None]:  # type: ignore[no-untyped-def]
    with TestClient(sqlite_app) as c:
        yield c


# ---------------------------------------------------------------------------
# Fixtures para tests de integración con PostgreSQL
# ---------------------------------------------------------------------------

def _postgres_available() -> bool:
    """Check if Postgres is available (via DATABASE_URL or default devcontainer URL)."""
    url = os.environ.get("DATABASE_URL", "")
    return url.startswith("postgresql")


@pytest.fixture()
def postgres_app():  # type: ignore[no-untyped-def]
    """App con PostgreSQL (requiere Docker/devcontainer corriendo)."""
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/legali")
    return create_app(configure_logs=False, persistence="postgres", database_url=db_url, run_worker=False)


@pytest.fixture()
def postgres_client(postgres_app) -> Generator[TestClient, None, None]:  # type: ignore[no-untyped-def]
    with TestClient(postgres_app) as c:
        # Clean tables before each test for isolation
        conn = postgres_app.state.db
        with conn.cursor() as cur:
            cur.execute("DELETE FROM idempotency_keys;")
            cur.execute("DELETE FROM transactions;")
            cur.execute("DELETE FROM summaries;")
        conn.commit()
        yield c


# Skip marker for postgres tests when not available
postgres_available = pytest.mark.skipif(
    not _postgres_available(),
    reason="PostgreSQL not available (set DATABASE_URL env var)",
)


# ---------------------------------------------------------------------------
# Fixtures para tests de integración con Redis (testcontainers)
# ---------------------------------------------------------------------------

def _testcontainers_available() -> bool:
    """Check if testcontainers can be used (Docker must be running)."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


# Skip marker for testcontainers tests
requires_docker = pytest.mark.skipif(
    not _testcontainers_available(),
    reason="Docker not available (required for testcontainers)",
)


@pytest.fixture(scope="module")
def redis_container():
    """
    Spin up a Redis container for integration tests.
    
    Uses testcontainers to automatically manage lifecycle.
    Scope=module means one container per test module (faster).
    """
    try:
        from testcontainers.redis import RedisContainer
    except ImportError:
        pytest.skip("testcontainers[redis] not installed")
    
    with RedisContainer() as redis:
        yield redis


@pytest.fixture
def redis_queue(redis_container):  # type: ignore[no-untyped-def]
    """RedisQueue connected to testcontainer."""
    from app.infra.queue import RedisQueue
    
    # Get connection URL from container
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{host}:{port}/0"
    
    queue = RedisQueue(redis_url=redis_url)
    queue.clear()  # Clean before each test
    return queue


@pytest.fixture
def redis_app(redis_queue):  # type: ignore[no-untyped-def]
    """App with Redis queue from testcontainer."""
    return create_app(
        configure_logs=False,
        persistence="memory",
        queue=redis_queue,
        run_worker=True,
    )


@pytest.fixture
def redis_client(redis_app) -> Generator[TestClient, None, None]:  # type: ignore[no-untyped-def]
    """TestClient with Redis queue."""
    with TestClient(redis_app) as c:
        yield c
