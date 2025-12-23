import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.logs import router as logs_router
from app.api.rpa import router as rpa_router
from app.api.summaries import router as summaries_router
from app.api.transactions import router as transactions_router
from app.api.websocket import ConnectionManager, create_event_handler, router as websocket_router
from app.infra.db import SqliteConfig, connect_sqlite, init_sqlite
from app.infra.event_log import get_event_log
from app.infra.events import EventBus, InMemoryEventBus
from app.infra.logging import configure_logging, get_logger
from app.infra.openai_client import OpenAIClient, create_openai_client
from app.infra.postgres import PostgresConfig, connect_postgres, init_postgres
from app.infra.queue import InMemoryQueue, QueueClient
from app.repos.in_memory import InMemoryIdempotencyStore, InMemorySummaryRepo, InMemoryTransactionRepo
from app.repos.postgres import PostgresIdempotencyStore, PostgresSummaryRepo, PostgresTransactionRepo
from app.repos.sqlite import SqliteIdempotencyStore, SqliteTransactionRepo
from app.services.summarize import SummarizeService
from app.settings import get_settings
from app.worker.handler import process_transaction


async def _run_worker(app: FastAPI, logger) -> None:  # type: ignore[no-untyped-def]
    """Background worker that processes jobs from the queue."""
    logger.info("worker.started")
    while True:
        try:
            job = app.state.queue.dequeue(timeout=1.0)
            if job is None:
                await asyncio.sleep(0.1)  # Yield to event loop
                continue

            job_id, job_type, payload = job
            logger.info("worker.job_received", job_id=job_id, job_type=job_type)

            if job_type == "process_transaction":
                tx_id = UUID(payload["transaction_id"])

                # Get old status before processing
                tx_before = app.state.transaction_repo.get(tx_id)
                old_status = tx_before.status.value if tx_before else "unknown"

                # Run in thread pool to not block event loop
                new_status = await asyncio.to_thread(
                    process_transaction,
                    app.state.transaction_repo,
                    tx_id,
                    simulate_work_seconds=0.5,  # Shorter for dev
                    fail_probability=0.1,
                    job_id=job_id,
                )

                # Publish event to WebSocket clients
                await app.state.event_bus.publish(
                    "transaction.status_changed",
                    {
                        "transaction_id": str(tx_id),
                        "old_status": old_status,
                        "new_status": new_status.value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            else:
                logger.warning("worker.unknown_job_type", job_type=job_type)

        except asyncio.CancelledError:
            logger.info("worker.stopped")
            break
        except Exception as e:
            logger.exception("worker.error", error=str(e))
            await asyncio.sleep(1.0)  # Back off on errors


def create_app(
    *,
    configure_logs: bool = True,
    persistence: Literal["memory", "sqlite", "postgres"] | None = None,
    database_url: str | None = None,
    queue: QueueClient | None = None,
    event_bus: EventBus | None = None,
    openai_client: OpenAIClient | None = None,
    run_worker: bool = True,
) -> FastAPI:
    """
    Application factory.

    Args:
        configure_logs: Whether to configure structlog (disable in tests to avoid noise).
        persistence: Override persistence mode ("memory", "sqlite", "postgres").
                     If None, inferred from DATABASE_URL env var.
        database_url: Override database URL. If None, read from env.
        queue: Override queue client. If None, uses InMemoryQueue.
        event_bus: Override event bus. If None, uses InMemoryEventBus.
        openai_client: Override OpenAI client. If None, created from OPENAI_API_KEY env var.
        run_worker: Whether to run the background worker (disable in some tests).
    """
    settings = get_settings()

    if configure_logs:
        configure_logging(service_name="api", json_output=settings.log_json)

    logger = get_logger(__name__)

    # Resolve persistence mode
    effective_persistence = persistence or settings.persistence_mode
    effective_db_url = database_url or settings.database_url

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if effective_persistence == "postgres":
            conn = connect_postgres(PostgresConfig(dsn=effective_db_url))
            init_postgres(conn)
            app.state.db = conn
            app.state.transaction_repo = PostgresTransactionRepo(conn)
            app.state.idempotency_store = PostgresIdempotencyStore(conn)
            app.state.summary_repo = PostgresSummaryRepo(conn)
        elif effective_persistence == "sqlite":
            # Extract path from sqlite:// URL or use as-is
            sqlite_path = effective_db_url
            if sqlite_path.startswith("sqlite://"):
                sqlite_path = sqlite_path.replace("sqlite://", "") or ":memory:"
            conn = connect_sqlite(SqliteConfig(path=sqlite_path))
            init_sqlite(conn)
            app.state.db = conn
            app.state.transaction_repo = SqliteTransactionRepo(conn)
            app.state.idempotency_store = SqliteIdempotencyStore(conn)
            app.state.summary_repo = InMemorySummaryRepo()
        else:
            # In-memory (default for tests)
            app.state.transaction_repo = InMemoryTransactionRepo()
            app.state.idempotency_store = InMemoryIdempotencyStore()
            app.state.summary_repo = InMemorySummaryRepo()

        # Setup queue
        app.state.queue = queue if queue is not None else InMemoryQueue()

        # Setup event bus and connection manager for WebSocket
        app.state.event_bus = event_bus if event_bus is not None else InMemoryEventBus()
        app.state.connection_manager = ConnectionManager()

        # Subscribe connection manager to broadcast events to WebSocket clients
        ws_handler = await create_event_handler(app.state.connection_manager)
        app.state.event_bus.subscribe("transaction.status_changed", ws_handler)

        # Subscribe event log to capture all events for the log viewer
        event_log = get_event_log()
        app.state.event_log = event_log

        async def log_event_handler(event_type: str, payload: dict) -> None:
            event_log.append(
                event_type,
                service="worker" if "job" in str(payload) else "api",
                request_id=payload.get("request_id", "-"),
                transaction_id=payload.get("transaction_id"),
                job_id=payload.get("job_id"),
                **{k: v for k, v in payload.items() if k not in ("request_id", "transaction_id", "job_id")},
            )

        app.state.event_bus.subscribe("*", log_event_handler)

        # Setup OpenAI client and SummarizeService
        app.state.openai_client = (
            openai_client
            if openai_client is not None
            else create_openai_client(settings.openai_api_key)
        )
        app.state.summarize_service = SummarizeService(
            openai_client=app.state.openai_client,
            summary_repo=app.state.summary_repo,
        )

        logger.info(
            "app.startup",
            persistence=effective_persistence,
            database_url=effective_db_url[:30] + "..." if len(effective_db_url) > 30 else effective_db_url,
            run_worker=run_worker,
        )

        # Start background worker if enabled
        worker_task = None
        if run_worker:
            worker_task = asyncio.create_task(_run_worker(app, logger))

        yield

        # Cleanup
        if worker_task is not None:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass

        conn = getattr(app.state, "db", None)
        if conn is not None:
            conn.close()
            logger.info("app.shutdown", persistence=effective_persistence)

    app = FastAPI(title="Legali API", lifespan=lifespan)

    # CORS for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        CorrelationIdMiddleware,
        validator=None,  # Accept any format for X-Request-Id
    )

    app.include_router(transactions_router)
    app.include_router(summaries_router)
    app.include_router(websocket_router)
    app.include_router(logs_router)
    app.include_router(rpa_router)

    @app.get("/health")
    def health() -> dict:
        logger.info("health.ok")
        return {"status": "ok"}

    return app


app = create_app()
