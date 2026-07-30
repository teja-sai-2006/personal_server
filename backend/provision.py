import asyncio
import sys
import secrets
from datetime import datetime, timedelta
from sqlalchemy.future import select

# Append backend dir to path so we can import app modules
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db, AsyncSessionLocal, User, InviteLink

async def provision_user(username: str):
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Check if exists
        result = await session.execute(select(User).filter(User.username == username))
        existing_user = result.scalars().first()
        if existing_user:
            print(f"Error: User '{username}' already exists.")
            return

        # Check if invite link exists, then delete it to create a new one
        result = await session.execute(select(InviteLink).filter(InviteLink.username == username))
        existing_invite = result.scalars().first()
        if existing_invite:
            await session.delete(existing_invite)
            
        print(f"Generating Invite Link for User: {username}")
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        new_invite = InviteLink(token=token, username=username, expires_at=expires_at)
        session.add(new_invite)
        await session.commit()
        
        print("\n" + "="*50)
        print("🎉 INVITE LINK SUCCESSFULLY GENERATED 🎉")
        print("="*50)
        print(f"Username: {username}")
        print(f"Expires In: 24 Hours")
        print("-" * 50)
        print("Send the appropriate link below to the user to complete registration:")
        print(f"Local Access:    http://localhost:8081/#invite={token}")
        print(f"Remote (Tailscale): http://<your-tailscale-ip>:8081/#invite={token}")
        print("="*50 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python provision.py <username>")
        sys.exit(1)
        
    username = sys.argv[1].lower()
    asyncio.run(provision_user(username))
