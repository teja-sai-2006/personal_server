import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import httpx
from .auth import get_current_user, User, active_sessions
from .database import get_db, SharedItem

router = APIRouter()

@router.get("/telemetry")
async def get_telemetry(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Returns live system telemetry for the dashboard."""
    # CPU usage over a short interval (non-blocking in async context if interval=None)
    cpu_percent = psutil.cpu_percent(interval=None)
    
    # RAM usage
    virtual_mem = psutil.virtual_memory()
    ram_gb = virtual_mem.used / (1024 ** 3)
    
    active_users_count = len(active_sessions)
    
    # Check shared items expiring within 24h
    now = datetime.utcnow()
    soon = now + timedelta(hours=24)
    result = await db.execute(
        select(SharedItem)
        .filter(SharedItem.target_user_id == current_user.id)
        .filter(SharedItem.expires_at > now)
        .filter(SharedItem.expires_at <= soon)
    )
    expiring_soon_count = len(result.scalars().all())
    
    # Check AI Status
    ai_status = "Offline"
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            res = await client.get("http://127.0.0.1:11434/")
            if res.status_code == 200:
                ai_status = "Ready"
    except:
        pass
    
    return {
        "cpu_percent": round(cpu_percent, 1),
        "ram_gb": round(ram_gb, 1),
        "active_users": active_users_count,
        "status": "Online",
        "shared_expiring_soon": expiring_soon_count,
        "ai_status": ai_status
    }
