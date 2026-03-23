#!/usr/bin/env python3
"""Quick config verification and DB init."""
import sys, os, asyncio

os.chdir('/mnt/r/MACHINE/MACHINE/backend')
sys.path.insert(0, '.')

# 1. Verify config loads
print("=== Config Check ===")
from app.core.config import settings
print(f"APP_ENV:  {settings.APP_ENV}")
print(f"DEBUG:    {settings.DEBUG}")
print(f"DB URL:   {settings.DATABASE_URL[:50]}...")
print(f"CORS:     {settings.CORS_ORIGINS}")
print()

# 2. Initialize DB
print("=== Database Init ===")
from app.core.database import Base, engine
from app.models import *  # Import all models so metadata is populated

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✅ All tables created successfully")

asyncio.run(init())

print()
print("=== All Done — ready to start the server ===")
