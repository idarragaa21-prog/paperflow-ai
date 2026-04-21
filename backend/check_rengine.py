import asyncio
import httpx

async def main():
    try:
        r = await httpx.AsyncClient().get('http://127.0.0.1:8010/health')
        print(r.status_code)
    except Exception as e:
        print(e)

asyncio.run(main())
