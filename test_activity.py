import asyncio
from WSClient import WSClient

CLIENT_KEY = "test_activity"

STEPS = [
    {"id": "1", "name": "Check sensors", "finished": False},
    {"id": "2", "name": "Calibrate motors", "finished": False},
    {"id": "3", "name": "Run diagnostics", "finished": False},
]

if __name__ == "__main__":
    client = WSClient()
    asyncio.run(client.run(CLIENT_KEY, STEPS))
