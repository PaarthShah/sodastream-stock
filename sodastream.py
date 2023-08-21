import asyncio
import logging
import os
import sys
from datetime import timedelta
from signal import SIGINT, SIGTERM
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from httpx import AsyncClient
from tqdm.asyncio import tqdm

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler(stream=sys.stdout)
stream_handler.setFormatter(formatter)

logger = logging.getLogger("sodastream.py")
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

BASE_URL = "https://sodastream.com/products/"
MONITORED = [
    "diet-caffeine-free-cola",
    "diet-caffeine-free-cola-4-pack",
]
ALL_MONITORED = [urljoin(BASE_URL, url) for url in MONITORED]

WEBHOOK_URL = os.environ["WEBHOOK_URL"]

interval = timedelta(minutes=5).total_seconds()

cookies = {
    'localization': 'US',
    'dy_fs_page': 'sodastream.com',
    '_dy_geo': 'US.NA.US_CA.US_CA_San%20Jose',
    '_dy_df_geo': 'United%20States.California.San%20Jose',
    'cart_currency': 'USD',
}
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://sodastream.com/collections/sparkling-water-flavors',
    'DNT': '1',
    'Alt-Used': 'sodastream.com',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
}


async def in_stock(client: AsyncClient) -> bool:
    _in_stock = False
    tasks = [
        asyncio.ensure_future(client.get(url, cookies=cookies, headers=headers, timeout=3))
        for url in ALL_MONITORED
    ]
    for coro in tqdm.as_completed(tasks):
        response = await coro
        if not response.text:
            pass
        soup = BeautifulSoup(response.text, features="html.parser")
        button_text = soup.find("button", {"name": "add"}).find("div").text.strip()
        match button_text:
            case "Sold Out": continue
            case "Buy Now": _in_stock = True
            case _:
                logger.warning(f"Unexpected button text {button_text}. Triggering for visibility.")
                _in_stock = True
    if _in_stock:
        logger.info("IT'S IN STOCK!!")
    else:
        logger.info("Nothing in stock yet.")
    return _in_stock


async def post_stock() -> None:
    async with AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.post(WEBHOOK_URL, json={"in_stock": await in_stock(client)})
            response.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Error during run.")
        logger.debug("Successfully called homeassistant webhook")


async def monitor_stock():
    try:
        while True:
            run = asyncio.ensure_future(post_stock())
            await asyncio.sleep(interval)
            await run
    except asyncio.CancelledError:
        logger.info("Got termination signal")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(monitor_stock())
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)
    loop.run_until_complete(main_task)
