"""Operator endpoints for the local, Obsidian-readable company brain."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.brain.service import BrainService, BrainUnavailable
from app.config import settings
from app.models import ActorContext
from app.security.identity import resolve_actor

router = APIRouter(prefix="/brain", tags=["Brain"], dependencies=[Depends(resolve_actor)])


class BrainQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class BrainSource(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=24000)


def _service() -> BrainService:
    return BrainService(settings.brain_vault_path, settings.poseidon_db_path)


@router.get("/status")
def status() -> dict:
    return _service().status()


@router.get("/nodes")
def list_nodes(actor: ActorContext = Depends(resolve_actor)) -> list[dict]:
    return _service().list_nodes(actor.owner_id)


@router.get("/graph")
def graph(actor: ActorContext = Depends(resolve_actor)) -> dict:
    return _service().graph(actor.owner_id)


@router.get("/nodes/{node_id}")
def get_node(node_id: str, actor: ActorContext = Depends(resolve_actor)) -> dict:
    node = _service().get_node(actor.owner_id, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Brain topic not found")
    return node


@router.post("/sync")
async def sync(actor: ActorContext = Depends(resolve_actor)) -> dict:
    try:
        return await _service().sync(actor.owner_id)
    except BrainUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sources")
async def add_source(payload: BrainSource, actor: ActorContext = Depends(resolve_actor)) -> dict:
    try:
        return await _service().add_source(actor.owner_id, payload.title, payload.text)
    except BrainUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/query")
async def query(payload: BrainQuestion, actor: ActorContext = Depends(resolve_actor)) -> dict:
    try:
        return await _service().query(actor.owner_id, payload.question)
    except BrainUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/lint")
async def lint(actor: ActorContext = Depends(resolve_actor)) -> dict:
    try:
        return await _service().lint(actor.owner_id)
    except BrainUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
