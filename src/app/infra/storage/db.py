import aiosqlite
from pathlib import Path

DB_PATH = Path("data/app.db")

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS signals_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            symbol TEXT PRIMARY KEY,
            opened_at TEXT NOT NULL,
            entry_price REAL,
            note TEXT
        );
        """)
        await db.commit()

async def save_signals_snapshot(created_at_iso: str, payload_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO signals_snapshot (created_at, payload_json) VALUES (?, ?)",
            (created_at_iso, payload_json),
        )
        await db.commit()

async def load_latest_signals_snapshot() -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT payload_json FROM signals_snapshot ORDER BY id DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return row[0] if row else None

async def upsert_position(symbol: str, opened_at_iso: str, entry_price: float | None, note: str | None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO positions(symbol, opened_at, entry_price, note)
            VALUES(?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET
              opened_at=excluded.opened_at,
              entry_price=excluded.entry_price,
              note=excluded.note
            """,
            (symbol, opened_at_iso, entry_price, note),
        )
        await db.commit()

async def delete_position(symbol: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM positions WHERE symbol=?", (symbol,))
        await db.commit()

async def list_positions():
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT symbol, opened_at, entry_price, note FROM positions ORDER BY opened_at DESC")
        rows = await cur.fetchall()
        return [
            {"symbol": r[0], "opened_at": r[1], "entry_price": r[2], "note": r[3]}
            for r in rows
        ]