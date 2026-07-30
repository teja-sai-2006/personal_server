import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from .database import get_db, User, InviteLink, Media, PasswordItem, AuthItem, SharedItem
from .crypto import generate_random_key, encrypt_umk, generate_recovery_code, hash_recovery_code, decrypt_emk
from .auth import get_password_hash, active_sessions

router = APIRouter()

class RegisterRequest(BaseModel):
    token: str
    password: str

@router.post("/register")
async def register_user(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InviteLink).filter(InviteLink.token == req.token))
    invite = result.scalars().first()
    
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid or expired invite link.")
        
    if invite.expires_at < datetime.utcnow():
        await db.delete(invite)
        await db.commit()
        raise HTTPException(status_code=400, detail="Invite link has expired.")
        
    user_exists = await db.execute(select(User).filter(User.username == invite.username.lower()))
    if user_exists.scalars().first():
        await db.delete(invite)
        await db.commit()
        raise HTTPException(status_code=400, detail="User already exists.")
        
    umk = generate_random_key(32)
    emk = encrypt_umk(umk, req.password)
    
    # Generate True Recovery Keys
    recovery_code = generate_recovery_code()
    remk = encrypt_umk(umk, recovery_code)
    
    # Keep recovery_hash for schema compatibility (though we don't strictly need it anymore for recovery)
    rec_hash = hash_recovery_code(recovery_code)
    pass_hash = get_password_hash(req.password)
    
    new_user = User(
        username=invite.username.lower(),
        password_hash=pass_hash,
        emk=emk,
        remk=remk,
        recovery_hash=rec_hash
    )
    
    db.add(new_user)
    await db.delete(invite)
    await db.commit()
    
    return {"message": "Registration successful", "recovery_code": recovery_code, "username": invite.username}

class RecoverRequest(BaseModel):
    username: str
    recovery_code: str
    new_password: str

@router.post("/recover")
async def recover_user(req: RecoverRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == req.username.lower()))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.remk:
        raise HTTPException(status_code=400, detail="This account does not have True Data Recovery enabled. It must be recreated.")

    try:
        # Decrypt the User Master Key using the Recovery Code
        umk = decrypt_emk(user.remk, req.recovery_code)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid recovery code")
        
    # We successfully recovered the UMK! No data deletion needed!
    # Generate fresh keys to rotate them
    emk = encrypt_umk(umk, req.new_password)
    new_recovery_code = generate_recovery_code()
    new_remk = encrypt_umk(umk, new_recovery_code)
    
    user.recovery_hash = hash_recovery_code(new_recovery_code)
    user.password_hash = get_password_hash(req.new_password)
    user.emk = emk
    user.remk = new_remk
    
    await db.commit()
    
    if user.id in active_sessions:
        del active_sessions[user.id]
        
    return {"message": "Account successfully recovered", "new_recovery_code": new_recovery_code}
