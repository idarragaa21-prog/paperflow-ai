#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Creating default admin user if needed..."
python -c "
import asyncio, os
from app.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == 'demo@paperflow.ai'))
        if not result.scalars().first():
            user = User(
                email='demo@paperflow.ai',
                full_name='Demo User',
                hashed_password=get_password_hash('demo1234'),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            print('Created demo user: demo@paperflow.ai / demo1234')
        else:
            print('Demo user already exists')

asyncio.run(create_admin())
"

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
