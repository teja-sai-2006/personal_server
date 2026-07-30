import asyncio
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from .auth import get_current_user, User

router = APIRouter()

OLLAMA_URL = "http://127.0.0.1:11434"

class AIQueueState:
    def __init__(self):
        self.active_model = None
        self.active_users = set()
        self.last_activity = datetime.utcnow()
        self.lock = asyncio.Lock()
        
    async def get_status(self):
        async with self.lock:
            return {
                "active_model": self.active_model,
                "users_count": len(self.active_users),
                "idle_time_seconds": (datetime.utcnow() - self.last_activity).total_seconds()
            }

    async def update_activity(self):
        async with self.lock:
            self.last_activity = datetime.utcnow()

ai_state = AIQueueState()

async def unload_idle_model():
    """Background task to unload model if idle for 15 minutes."""
    while True:
        await asyncio.sleep(60)
        async with ai_state.lock:
            if ai_state.active_model and len(ai_state.active_users) == 0:
                idle_seconds = (datetime.utcnow() - ai_state.last_activity).total_seconds()
                if idle_seconds > 900:  # 15 minutes
                    # Unload via Ollama API
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(f"{OLLAMA_URL}/api/generate", json={
                                "model": ai_state.active_model,
                                "keep_alive": 0
                            })
                    except Exception as e:
                        print(f"Failed to unload model: {e}")
                    ai_state.active_model = None
                    print("Idle model unloaded.")

@router.on_event("startup")
async def start_background_tasks():
    asyncio.create_task(unload_idle_model())

@router.get("/status")
async def ai_status(current_user: User = Depends(get_current_user)):
    return await ai_state.get_status()

@router.get("/models")
async def ai_models(current_user: User = Depends(get_current_user)):
    """Fetches available models from Ollama."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                return response.json()
            return {"models": []}
    except Exception:
        return {"models": []}

@router.post("/chat")
async def chat_proxy(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Proxies request to Ollama with queue management."""
    body = await request.json()
    requested_model = body.get("model")
    
    if not requested_model:
        raise HTTPException(status_code=400, detail="Model must be specified")
        
    async with ai_state.lock:
        if ai_state.active_model and ai_state.active_model != requested_model:
            if len(ai_state.active_users) > 0:
                raise HTTPException(
                    status_code=429, 
                    detail=f"Model {ai_state.active_model} is currently active. "
                           f"Running {requested_model} requires unloading it. "
                           f"Please try again later or use the active model."
                )
        
        # Safe to switch or use current
        ai_state.active_model = requested_model
        ai_state.active_users.add(current_user.id)
        ai_state.last_activity = datetime.utcnow()
        
    try:
        # Proxy to Ollama
        async with httpx.AsyncClient() as client:
            # We are not streaming here for simplicity, but in prod we should use StreamingResponse
            # To keep it simple per design plan:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=120.0)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Ollama Error")
                
            return response.json()
            
    finally:
        async with ai_state.lock:
            ai_state.active_users.discard(current_user.id)
            ai_state.last_activity = datetime.utcnow()
