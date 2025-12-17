import asyncio
from common import run_client

CLIENT_KEY = "choice_activity"

CHOICES = [
    {"id": "1", "name": "Habit", "options": ["Option A", "Option B"], "chosen": -1,"authorized": False},
    {"id": "2", "name": "Discussion", "options": ["Option A", "Option B"], "chosen": -1,"authorized": False},
]

if __name__ == "__main__":
    asyncio.run(run_client(CLIENT_KEY, CHOICES))
