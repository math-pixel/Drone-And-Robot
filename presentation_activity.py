import asyncio
from common import run_client

CLIENT_KEY = "presentation_activity"

STEPS = [
    {"id": "1", "name": "Intro video", "finished": False},
    {"id": "2", "name": "Explain concept", "finished": False},
    {"id": "3", "name": "Audience interaction", "finished": False},
]

if __name__ == "__main__":
    asyncio.run(run_client(CLIENT_KEY, STEPS))
