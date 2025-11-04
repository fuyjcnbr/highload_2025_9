import json
import time
import datetime
import asyncio
import aiohttp
from signal import SIGINT, SIGTERM

# N = 20

async def insert():
    i = 0
    while True:
        i += 1
        data = {"data": "data" + str(i)}
        try:
            # async with asyncio.timeout(10):
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:8223/test/insert1", json=data) as resp:
                    text = await resp.text()
                    print(f"{datetime.datetime.now()} {resp.status}, {text}")
                time.sleep(0.3)
        # except TimeoutError:
        #     print(f"{datetime.datetime.now()} Timeout 10 sec exceeded")
        except Exception as e:
            print(f"{datetime.datetime.now()} exception: {e}")

# asyncio.run(insert())

async def main():
    try:
        await insert()
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(main())
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()
