"""Poseidon — FastAPI application entrypoint."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.gateway.web_adapter import router as web_router
from app.gateway.memory_adapter import router as memory_router


app = FastAPI(
    title="Poseidon Agent",
    description="Persistent-memory personal agent",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path
from fastapi.staticfiles import StaticFiles

app.include_router(web_router)
app.include_router(memory_router)


@app.get("/health")
async def health():
    return {"status": "ok", "model": settings.poseidon_model}


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
