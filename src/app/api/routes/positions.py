from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from ...infra.storage.db import list_positions, upsert_position, delete_position

router = APIRouter()

class OpenPositionIn(BaseModel):
    symbol: str
    entry_price: float | None = None
    note: str | None = None

@router.get("/positions")
async def get_positions():
    return {"positions": await list_positions()}

@router.post("/positions/open")
async def open_position(body: OpenPositionIn):
    opened_at = datetime.utcnow().isoformat()
    await upsert_position(body.symbol.upper(), opened_at, body.entry_price, body.note)
    return {"ok": True}

@router.post("/positions/close")
async def close_position(symbol: str):
    await delete_position(symbol.upper())
    return {"ok": True}