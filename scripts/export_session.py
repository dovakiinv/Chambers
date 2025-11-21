import asyncio
import aiosqlite
import sys
from pathlib import Path
from datetime import datetime

# Ensure path is correct for imports
sys.path.append(str(Path(__file__).parent.parent))

from chambers.database import DB_PATH

async def export_latest_session():
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get latest session
        async with db.execute("SELECT * FROM sessions ORDER BY last_updated DESC LIMIT 1") as cursor:
            session = await cursor.fetchone()
            
        if not session:
            print("❌ No sessions found.")
            return

        session_id = session["id"]
        print(f"📜 Exporting Session: {session_id}")
        print(f"📅 Created: {session['created_at']}")

        # Get messages
        async with db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", 
            (session_id,)
        ) as cursor:
            messages = await cursor.fetchall()

    # Format Markdown
    output_lines = [
        f"# Skyforge Chambers Session: {session_id}",
        f"**Date:** {session['created_at']}",
        f"**Messages:** {len(messages)}",
        "",
        "---",
        ""
    ]

    for msg in messages:
        timestamp = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
        speaker = msg["speaker"].upper()
        content = msg["content"]
        
        output_lines.append(f"### 🕒 {timestamp} - **{speaker}**")
        output_lines.append("")
        output_lines.append(content)
        output_lines.append("")
        output_lines.append("---")
        output_lines.append("")

    filename = "latest_session.md"
    with open(filename, "w") as f:
        f.write("\n".join(output_lines))

    print(f"✅ Export complete: {Path(filename).absolute()}")

if __name__ == "__main__":
    asyncio.run(export_latest_session())
