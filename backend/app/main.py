"""Poseidon — FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import settings
from app.llm_providers import llm_provider
from app.gateway.web_adapter import router as web_router
from app.gateway.telegram_adapter import router as telegram_router, poller as telegram_poller
from app.gateway.memory_adapter import router as memory_router
from app.gateway.agents_adapter import router as agents_router
from app.gateway.trajectory_adapter import router as trajectory_router
from app.db.migrations import apply_migrations
from app.db.connection import connection
from app.startup_checks import check_runtime
from app.security.identity import resolve_actor, validate_network_config
from app.orchestration.graph import HarnessRuntime, HarnessServices, set_runtime
from app.orchestration.approval_store import ApprovalStore
from app.security.secrets import redact


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_network_config()
    app.state.capabilities = check_runtime()
    apply_migrations(settings.poseidon_db_path, settings.poseidon_embedding_dim)
    with connection(settings.poseidon_db_path) as conn:
        vector_schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='vec_episodes'").fetchone()[0]
        if 'USING vec0' not in vector_schema:
            app.state.capabilities['vector_mode'] = 'python-cosine'
    try:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    except ImportError:
        raise RuntimeError('Durable runtime requires langgraph-checkpoint-sqlite and aiosqlite') from None
    async with AsyncSqliteSaver.from_conn_string(str(settings.poseidon_db_path)) as saver:
        await saver.setup()
        await saver.conn.execute('PRAGMA journal_mode=WAL')
        await saver.conn.execute('PRAGMA busy_timeout=5000')
        await saver.conn.execute('PRAGMA foreign_keys=ON')
        await saver.conn.commit()
        runtime = HarnessRuntime(saver, HarnessServices(approvals=ApprovalStore(settings.poseidon_db_path)))
        app.state.runtime = runtime
        set_runtime(runtime)
        try:
            await runtime.reconcile_approvals()
            # Rewrite legacy plaintext provider overrides using credential references.
            if llm_provider._config_path.exists():
                llm_provider.save_config()
            if settings.telegram_polling_enabled and settings.telegram_bot_token:
                telegram_poller.start()
            yield
        finally:
            telegram_poller.stop()
            if telegram_poller._task:
                import asyncio
                await asyncio.gather(telegram_poller._task, return_exceptions=True)
            set_runtime(None)
            app.state.runtime = None


app = FastAPI(
    title="Poseidon Agent",
    description="Persistent-memory personal agent harness",
    version="0.5.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic's default response echoes rejected inputs, including submitted keys.
    errors = [{k: redact(v) for k, v in error.items() if k in {'type', 'loc', 'msg'}} for error in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': errors})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.poseidon_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_router, dependencies=[Depends(resolve_actor)])
app.include_router(telegram_router)
app.include_router(memory_router, dependencies=[Depends(resolve_actor)])
app.include_router(agents_router, dependencies=[Depends(resolve_actor)])
app.include_router(trajectory_router, dependencies=[Depends(resolve_actor)])


@app.get("/health")
async def health():
    primary = llm_provider.get_agent_resolved_config("poseidon")
    return {
        "status": "ok",
        "model": primary.get("model", settings.poseidon_model),
        "provider": primary.get("preset", "env"),
        "configured": primary.get("has_api_key", False),
        "mode": "local-first",
        "telegram_polling": settings.telegram_polling_enabled and bool(settings.telegram_bot_token),
        "capabilities": getattr(app.state, 'capabilities', {}),
    }


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.poseidon_host,
        port=settings.poseidon_port,
        reload=True,
    )
