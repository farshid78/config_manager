import asyncio
from core.logger import setup_logging
import main as m

setup_logging()
app = m.build_application()


async def t():
    try:
        await app.initialize()
        print("initialized ok")
    finally:
        await app.shutdown()


asyncio.run(t())
