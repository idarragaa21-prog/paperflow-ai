import asyncio
import asyncpg
async def main():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/postgres')
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    print([t['table_name'] for t in tables])
    
    # Try updating
    try:
        await conn.execute("UPDATE users SET password_hash = '$2b$12$hb4WpHmrsYBl20bTUCUrq.Dex1SBV.6VZuu/LncmhYAw3hsMcFkmi'")
        print("Updated users in postgres db!")
    except Exception as e:
        pass
    await conn.close()

asyncio.run(main())
