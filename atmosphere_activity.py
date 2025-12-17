import asyncio
from common import run_client

CLIENT_KEY = "atmosphere_activity"

if __name__ == "__main__":
    asyncio.run(run_client(CLIENT_KEY))
