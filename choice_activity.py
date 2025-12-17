import asyncio
from common import run_client

CLIENT_KEY = "choice_activity"

STEPS = [
    {"id": 1, "actions":[
        {"id": 1,"type": "video", "file": "video1.mp4", "finished": False},
        {"id": 2,"type": "choice", "name": "Habit", "options": ["Option A", "Option B"], "chosen": -1}
    ], "authorized": False, "finished": False},
    {"id": 2, "actions":[
        {"id": 1,"type": "video", "file": "video2.mp4", "finished": False},
        {"id": 2,"type": "choice", "name": "Color", "options": ["Red", "Blue"], "chosen": -1}
    ], "authorized": False, "finished": False},
]


if __name__ == "__main__":
    asyncio.run(run_client(CLIENT_KEY, STEPS))
