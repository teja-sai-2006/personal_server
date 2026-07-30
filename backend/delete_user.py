import asyncio
import sys

# Append backend dir to path
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.future import select
from app.database import init_db, AsyncSessionLocal, User

async def delete_user(username: str):
    await init_db()
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).filter(User.username == username))
        user = result.scalars().first()
        
        if not user:
            print(f"User '{username}' not found.")
            return
            
        await session.delete(user)
        await session.commit()
        print(f"Successfully deleted user '{username}' from the database.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_user.py <username>")
        sys.exit(1)
        
    username = sys.argv[1]
    asyncio.run(delete_user(username))
