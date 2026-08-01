import asyncio
from aiohttp import ClientSession, TCPConnector, ThreadedResolver

async def main():
    connector = TCPConnector(
        resolver=ThreadedResolver()
    )

    async with ClientSession(connector=connector) as session:
        async with session.get("https://api.telegram.org") as resp:
            print(resp.status)
            print(await resp.text())

asyncio.run(main())