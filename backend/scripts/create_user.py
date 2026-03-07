from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.database import async_session_maker
from app.models.user import User


async def _run(email: str, password: str, full_name: str | None) -> None:
    async with async_session_maker() as session:
        q = await session.execute(select(User).where(User.email == email).limit(1))
        existing = q.scalar_one_or_none()
        if existing:
            raise SystemExit(f"User already exists: {email}")

        u = User(email=email, password_hash=hash_password(password), full_name=full_name, is_active=True)
        session.add(u)
        await session.commit()
        await session.refresh(u)
        print(f"Created user: {u.id} {u.email}")


def main() -> None:
    p = argparse.ArgumentParser(description="Create a local user (dev)")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--full-name", default=None)
    args = p.parse_args()

    asyncio.run(_run(args.email, args.password, args.full_name))


if __name__ == "__main__":
    main()
