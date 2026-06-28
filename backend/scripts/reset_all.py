import asyncio
from sqlalchemy import update
from app.core.security import hash_password
from app.database import async_session_maker
from app.models.user import User

async def main():
    async with async_session_maker() as session:
        new_pass = hash_password('admin123')
        await session.execute(update(User).values(password_hash=new_pass))
        await session.commit()
        print("Updated all users with password: admin123")

if __name__ == "__main__":
    asyncio.run(main())
