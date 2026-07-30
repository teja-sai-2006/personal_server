import os
import aiofiles
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Form
from typing import List
from fastapi.responses import StreamingResponse
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import base64

from .database import get_db, User, Media, SharedItem, BASE_DIR
from .auth import get_current_user, get_active_umk
from .crypto import encrypt_file_data, decrypt_file_data, generate_random_key

router = APIRouter()

MEDIA_DIR = os.path.join(BASE_DIR, "data", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

@router.post("/upload")
async def upload_media(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    """Encrypts and uploads multiple files using the user's active UMK."""
    uploaded_ids = []
    
    for file in files:
        file_data = await file.read()
        encrypted_data = encrypt_file_data(file_data, umk)
        
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(MEDIA_DIR, unique_filename)
        
        async with aiofiles.open(filepath, 'wb') as out_file:
            await out_file.write(encrypted_data)
            
        new_media = Media(
            owner_id=current_user.id,
            filename=file.filename,
            filepath=filepath,
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(file_data)
        )
        db.add(new_media)
        await db.commit()
        await db.refresh(new_media)
        uploaded_ids.append(new_media.id)
        
    return {"message": f"{len(files)} files encrypted and uploaded", "media_ids": uploaded_ids}

@router.get("/download/{media_id}")
async def download_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    """Decrypts and streams a file to the owner."""
    result = await db.execute(select(Media).filter(Media.id == media_id, Media.owner_id == current_user.id))
    media = result.scalars().first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    async with aiofiles.open(media.filepath, 'rb') as f:
        encrypted_data = await f.read()
        
    try:
        decrypted_data = decrypt_file_data(encrypted_data, umk)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to decrypt file")
        
    # Yield decrypted data for streaming response
    def iterfile():
        yield decrypted_data
        
    return StreamingResponse(iterfile(), media_type=media.mime_type, headers={
        "Content-Disposition": f"inline; filename={media.filename}"
    })

@router.post("/share/{media_id}")
async def share_media(
    media_id: int,
    target_username: str = Form(...),
    expires_in_hours: int = Form(24),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    umk: bytes = Depends(get_active_umk)
):
    """Shares a file with another user via an Ephemeral Folder Key (EFK)."""
    # 1. Fetch Media and Target User
    result = await db.execute(select(Media).filter(Media.id == media_id, Media.owner_id == current_user.id))
    media = result.scalars().first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    target_result = await db.execute(select(User).filter(User.username == target_username))
    target_user = target_result.scalars().first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
        
    if expires_in_hours < 1 or expires_in_hours > 168:
        raise HTTPException(status_code=400, detail="Expiration must be between 1 hour and 7 days (168 hours)")
        
    # 2. Decrypt original file with UMK
    async with aiofiles.open(media.filepath, 'rb') as f:
        encrypted_data = await f.read()
    decrypted_data = decrypt_file_data(encrypted_data, umk)
    
    # 3. Generate EFK and Re-encrypt
    efk = generate_random_key(32)
    efk_encrypted_data = encrypt_file_data(decrypted_data, efk)
    
    # 4. Save ephemeral file
    ephemeral_filepath = f"{media.filepath}.share_{uuid.uuid4().hex}"
    async with aiofiles.open(ephemeral_filepath, 'wb') as f:
        await f.write(efk_encrypted_data)
        
    # 5. Store in DB
    # We encrypt the EFK with the target user's public key or just store it in DB (since this is internal)
    # The architecture states "User B can access.. even if User A is logged out". 
    # For a completely zero-trust model, we should encrypt EFK with Target User's public key.
    # To simplify per design, EFK is stored in the DB (only accessible to the server).
    
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    share = SharedItem(
        owner_id=current_user.id,
        target_user_id=target_user.id,
        media_id=media.id,
        efk=base64.b64encode(efk).decode('utf-8'),
        ephemeral_filepath=ephemeral_filepath,
        expires_at=expires_at
    )
    db.add(share)
    await db.commit()
    
    return {"message": f"Shared with {target_username}", "expires_at": expires_at}

@router.get("/list")
async def list_media(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists all media owned by the current user."""
    result = await db.execute(select(Media).filter(Media.owner_id == current_user.id))
    media_items = result.scalars().all()
    
    return [
        {
            "id": m.id,
            "filename": m.filename,
            "mime_type": m.mime_type,
            "size_bytes": m.size_bytes,
            "uploaded_at": m.uploaded_at
        } for m in media_items
    ]

@router.get("/shared")
async def list_shared(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists media shared with the current user."""
    result = await db.execute(
        select(SharedItem, Media)
        .join(Media, SharedItem.media_id == Media.id)
        .filter(SharedItem.target_user_id == current_user.id)
    )
    
    shared_items = []
    for share, media in result.all():
        if share.expires_at > datetime.utcnow():
            shared_items.append({
                "share_id": share.id,
                "media_id": media.id,
                "filename": media.filename,
                "expires_at": share.expires_at
            })
            
    return shared_items

@router.get("/download/shared/{share_id}")
async def download_shared_media(
    share_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Downloads a shared item by decrypting it with its Ephemeral Folder Key (EFK)."""
    result = await db.execute(
        select(SharedItem, Media)
        .join(Media, SharedItem.media_id == Media.id)
        .filter(SharedItem.id == share_id, SharedItem.target_user_id == current_user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Shared item not found or unauthorized")
        
    share, media = row
    
    if share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=403, detail="Shared item has expired")
        
    if not share.ephemeral_filepath or not os.path.exists(share.ephemeral_filepath):
        raise HTTPException(status_code=404, detail="Ephemeral file not found")
        
    # Read encrypted data
    async with aiofiles.open(share.ephemeral_filepath, 'rb') as f:
        encrypted_data = await f.read()
        
    # Decode EFK and Decrypt
    efk = base64.b64decode(share.efk)
    decrypted_data = decrypt_file_data(encrypted_data, efk)
    
    # Stream response
    def iterfile():
        yield decrypted_data
        
    return StreamingResponse(iterfile(), media_type=media.mime_type, headers={
        "Content-Disposition": f"inline; filename={media.filename}"
    })

@router.get("/shared/by_me")
async def list_shared_by_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists media the current user is sharing with others."""
    result = await db.execute(
        select(SharedItem, Media, User)
        .join(Media, SharedItem.media_id == Media.id)
        .join(User, SharedItem.target_user_id == User.id)
        .filter(SharedItem.owner_id == current_user.id)
    )
    
    shared_items = []
    for share, media, target_user in result.all():
        if share.expires_at > datetime.utcnow():
            shared_items.append({
                "share_id": share.id,
                "media_id": media.id,
                "filename": media.filename,
                "target_username": target_user.username,
                "expires_at": share.expires_at
            })
            
    return shared_items

async def secure_shred(filepath: str):
    """Overwrites file with random bytes before deleting."""
    if not os.path.exists(filepath):
        return
    size = os.path.getsize(filepath)
    try:
        with open(filepath, 'r+b') as f:
            f.write(os.urandom(size))
        os.remove(filepath)
    except Exception as e:
        print(f"Error shredding file {filepath}: {e}")

@router.delete("/delete/{media_id}")
async def delete_media(
    media_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deletes a file from the database and securely shreds it from disk."""
    result = await db.execute(select(Media).filter(Media.id == media_id, Media.owner_id == current_user.id))
    media = result.scalars().first()
    
    if not media:
        raise HTTPException(status_code=404, detail="Media not found or unauthorized")
        
    filepath = media.filepath
    
    # Remove DB entry
    await db.delete(media)
    await db.commit()
    
    # Shred file in background so API is responsive
    background_tasks.add_task(secure_shred, filepath)
    
    return {"message": "File deleted and scheduled for secure shredding"}

@router.delete("/shared/{share_id}")
async def revoke_share(
    share_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revokes a share and securely shreds its ephemeral key file."""
    result = await db.execute(select(SharedItem).filter(SharedItem.id == share_id, SharedItem.owner_id == current_user.id))
    share = result.scalars().first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Shared item not found or unauthorized")
        
    if share.ephemeral_filepath:
        background_tasks.add_task(secure_shred, share.ephemeral_filepath)
        
    await db.delete(share)
    await db.commit()
    
    return {"message": "Share revoked"}
