import httpx
import asyncio

async def test_r_engine():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("http://127.0.0.1:8010/health")
            print(resp.status_code)
            print(resp.text)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_r_engine())
