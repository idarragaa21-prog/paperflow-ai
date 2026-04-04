import asyncio
import asyncpg
async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/paperflow_ai')
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        print([t['table_name'] for t in tables])
        
        await conn.execute("UPDATE users SET password_hash = '$2b$12$hb4WpHmrsYBl20bTUCUrq.Dex1SBV.6VZuu/LncmhYAw3hsMcFkmi'")
        print("Updated users!")
        await conn.close()
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
