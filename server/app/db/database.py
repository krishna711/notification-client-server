import aiosqlite
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from ..core.config import settings

logger = logging.getLogger("notification_server.db")

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager for SQLite connection with WAL mode."""
    conn = await aiosqlite.connect(settings.DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
    finally:
        await conn.close()

# For backward compatibility if needed
get_db_connection = get_db

async def init_db():
    """Initialize database tables with WAL mode for fast concurrent async writes."""
    async with get_db() as db:
        # Table: notifications
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                category TEXT DEFAULT 'general',
                target_device TEXT DEFAULT 'all',
                payload_data TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'pending',
                delivered_at TIMESTAMP NULL,
                acknowledged_at TIMESTAMP NULL
            );
        """)
        
        # Indexes for fast lookup
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_status 
            ON notifications(status);
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_target 
            ON notifications(target_device, status);
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notifications_created 
            ON notifications(created_at DESC);
        """)

        # Table: devices
        await db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_name TEXT NOT NULL,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_online INTEGER DEFAULT 0,
                ip_address TEXT,
                client_version TEXT
            );
        """)
        
        await db.commit()
        logger.info("Database initialized successfully with WAL mode.")
