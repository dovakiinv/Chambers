import aiosqlite
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import json

DB_PATH = Path("chambers.db")

INIT_SCRIPT = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    last_updated TIMESTAMP,
    status TEXT,
    rotation_state TEXT  -- JSON blob for rotation markers
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    speaker TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    metadata TEXT,  -- JSON blob for extra data (tokens, model used)
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""

async def init_db():
    """Initialize the database with schema and WAL mode."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(INIT_SCRIPT)
        await db.commit()

async def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO sessions (id, created_at, last_updated, status, rotation_state) VALUES (?, ?, ?, ?, ?)",
            (session_id, now, now, "active", "{}")
        )
        await db.commit()
    return session_id

async def save_message(session_id: str, speaker: str, content: str, metadata: Dict[str, Any] = None):
    """Save a message to the database."""
    now = datetime.now().isoformat()
    meta_json = json.dumps(metadata or {})
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (session_id, speaker, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (session_id, speaker, content, now, meta_json)
        )
        # Update session timestamp
        await db.execute(
            "UPDATE sessions SET last_updated = ? WHERE id = ?",
            (now, session_id)
        )
        await db.commit()

async def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    """Retrieve all messages for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
