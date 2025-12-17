import asyncio
from common import run_client

WS_URL = "ws://192.168.1.13:8057/ws"
CLIENT_KEY = "test_activity"

STEPS = [
    {"id": "1", "name": "Check sensors", "finished": False},
    {"id": "2", "name": "Calibrate motors", "finished": False},
    {"id": "3", "name": "Run diagnostics", "finished": False},
]

if __name__ == "__main__":
    asyncio.run(run_client(WS_URL, CLIENT_KEY, STEPS))
