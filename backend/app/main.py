from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from .database import init_db, get_db, User
from .auth import verify_password, create_access_token, active_sessions, ACCESS_TOKEN_EXPIRE_MINUTES
from .crypto import decrypt_emk
from . import media, ai, monitoring, passwords, auth_routes

app = FastAPI(title="Personal Server API")

# Setup CORS (even though it's locally bound, good practice for SPA)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await init_db()
    # Trigger background tasks for AI if needed
    await ai.start_background_tasks()

@app.post("/api/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Authenticates user and loads decrypted UMK into memory cache."""
    result = await db.execute(select(User).filter(User.username == form_data.username.lower()))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # Decrypt the EMK to get the UMK using the password provided
        umk = decrypt_emk(user.emk, form_data.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Decryption failed. Invalid credentials or corrupt key.")
        
    # Store UMK in active session memory
    active_sessions[user.id] = umk
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Include routers
app.include_router(media.router, prefix="/api/media", tags=["media"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(monitoring.router, prefix="/api/system", tags=["monitoring"])
app.include_router(passwords.router, prefix="/api/vault", tags=["vault"])
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
