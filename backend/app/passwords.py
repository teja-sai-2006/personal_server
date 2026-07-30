from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List
import pyotp
import base64
import urllib.parse
from . import migration_pb2

from .database import get_db, User, PasswordItem, AuthItem
from .auth import get_current_user, get_active_umk
from .crypto import encrypt_file_data, decrypt_file_data

router = APIRouter()

class PasswordCreate(BaseModel):
    website: str
    username: str
    password: str

class PasswordResponse(BaseModel):
    id: int
    website: str
    username: str
    password: str # Decrypted for the frontend

class AuthCreate(BaseModel):
    name: str
    secret: str

class AuthResponse(BaseModel):
    id: int
    name: str
    code: str
    ttl: int

@router.post("/passwords", response_model=PasswordResponse)
async def create_password(
    item: PasswordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    encrypted_bytes = encrypt_file_data(item.password.encode('utf-8'), umk)
    encrypted_b64 = base64.b64encode(encrypted_bytes).decode('ascii')
    
    db_item = PasswordItem(
        owner_id=current_user.id,
        website=item.website,
        username=item.username,
        encrypted_password=encrypted_b64
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    
    return PasswordResponse(
        id=db_item.id,
        website=db_item.website,
        username=db_item.username,
        password=item.password
    )

@router.get("/passwords", response_model=List[PasswordResponse])
async def list_passwords(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    result = await db.execute(select(PasswordItem).filter(PasswordItem.owner_id == current_user.id))
    items = result.scalars().all()
    
    response = []
    for item in items:
        try:
            encrypted_bytes = base64.b64decode(item.encrypted_password)
            decrypted_bytes = decrypt_file_data(encrypted_bytes, umk)
            decrypted_pw = decrypted_bytes.decode('utf-8')
            response.append(PasswordResponse(
                id=item.id,
                website=item.website,
                username=item.username,
                password=decrypted_pw
            ))
        except Exception:
            pass 
            
    return response

@router.delete("/passwords/{item_id}")
async def delete_password(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(PasswordItem).filter(PasswordItem.id == item_id, PasswordItem.owner_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await db.delete(item)
    await db.commit()
    return {"message": "Deleted"}

@router.post("/auth", response_model=AuthResponse)
async def create_auth(
    item: AuthCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    try:
        totp = pyotp.TOTP(item.secret.replace(" ", "").upper())
        totp.now() 
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid TOTP secret")
        
    encrypted_bytes = encrypt_file_data(item.secret.encode('utf-8'), umk)
    encrypted_b64 = base64.b64encode(encrypted_bytes).decode('ascii')
    
    db_item = AuthItem(
        owner_id=current_user.id,
        name=item.name,
        encrypted_secret=encrypted_b64
    )
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    
    totp_code = totp.now()
    import time
    ttl = 30 - int(time.time()) % 30
    
    return AuthResponse(
        id=db_item.id,
        name=db_item.name,
        code=totp_code,
        ttl=ttl
    )

@router.get("/auth", response_model=List[AuthResponse])
async def list_auths(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    result = await db.execute(select(AuthItem).filter(AuthItem.owner_id == current_user.id))
    items = result.scalars().all()
    
    import time
    ttl = 30 - int(time.time()) % 30
    
    response = []
    for item in items:
        try:
            encrypted_bytes = base64.b64decode(item.encrypted_secret)
            decrypted_bytes = decrypt_file_data(encrypted_bytes, umk)
            secret = decrypted_bytes.decode('utf-8').replace(" ", "").upper()
            
            totp = pyotp.TOTP(secret)
            response.append(AuthResponse(
                id=item.id,
                name=item.name,
                code=totp.now(),
                ttl=ttl
            ))
        except Exception:
            pass
            
    return response

@router.delete("/auth/{item_id}")
async def delete_auth(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(AuthItem).filter(AuthItem.id == item_id, AuthItem.owner_id == current_user.id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    await db.delete(item)
    await db.commit()
    return {"message": "Deleted"}

class MigrationCreate(BaseModel):
    uri: str

@router.post("/auth/migration")
async def import_migration(
    item: MigrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    try:
        parsed = urllib.parse.urlparse(item.uri)
        qs = urllib.parse.parse_qs(parsed.query)
        if "data" not in qs:
            raise ValueError("No data parameter")
            
        b64str = qs["data"][0]
        # Pad urlsafe base64
        b64str += "=" * ((4 - len(b64str) % 4) % 4)
        data = base64.urlsafe_b64decode(b64str)
        
        payload = migration_pb2.MigrationPayload()
        payload.ParseFromString(data)
        
        imported_count = 0
        for otp in payload.otp_parameters:
            if not otp.secret:
                continue
                
            # Google auth migration secret is the raw bytes. PyOTP expects Base32.
            secret_b32 = base64.b32encode(otp.secret).decode('utf-8').replace("=", "")
            name = otp.name if otp.name else "Imported Account"
            if otp.issuer:
                name = f"{otp.issuer} ({name})"
                
            encrypted_bytes = encrypt_file_data(secret_b32.encode('utf-8'), umk)
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('ascii')
            
            db_item = AuthItem(
                owner_id=current_user.id,
                name=name,
                encrypted_secret=encrypted_b64
            )
            db.add(db_item)
            imported_count += 1
            
        await db.commit()
        return {"message": f"Imported {imported_count} authenticators"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse migration data: {str(e)}")

