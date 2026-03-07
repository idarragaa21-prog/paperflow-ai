from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.database import async_session_maker
from app.models.user import User


async def _run(email: str, password: str) -> None:
    async with async_session_maker() as session:
        q = await session.execute(select(User).where(User.email == email).limit(1))
        u = q.scalar_one_or_none()
        if not u:
            raise SystemExit(f"User not found: {email}")

        u.password_hash = hash_password(password)
        await session.commit()
        print(f"Password reset for: {u.id} {u.email}")


def main() -> None:
    p = argparse.ArgumentParser(description="Reset a local user's password (dev)")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    asyncio.run(_run(args.email, args.password))


if __name__ == "__main__":
    main()
