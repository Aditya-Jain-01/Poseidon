"""Poseidon — FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.llm_providers import llm_provider
from app.gateway.web_adapter import router as web_router
from app.gateway.telegram_adapter import router as telegram_router, poller as telegram_poller
from app.gateway.memory_adapter import router as memory_router
from app.gateway.agents_adapter import router as agents_router
from app.gateway.trajectory_adapter import router as trajectory_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: start local Telegram long-poller if configured
    if settings.telegram_polling_enabled and settings.telegram_bot_token:
        telegram_poller.start()
    yield
    # Shutdown: stop poller
    telegram_poller.stop()


app = FastAPI(
    title="Poseidon Agent",
    description="Persistent-memory personal agent harness",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(web_router)
app.include_router(telegram_router)
app.include_router(memory_router)
app.include_router(agents_router)
app.include_router(trajectory_router)


@app.get("/health")
async def health():
<<<<<<< Updated upstream
    primary = llm_provider.get_agent_resolved_config("octavious")
    return {
        "status": "ok",
        "model": primary["model"],
        "provider": primary["preset"],
        "configured": primary["has_api_key"],
=======
    return {
        "status": "ok",
        "model": settings.poseidon_model,
        "mode": "local-first",
        "telegram_polling": settings.telegram_polling_enabled and bool(settings.telegram_bot_token),
>>>>>>> Stashed changes
    }


# Serve built frontend if dist directory exists
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
