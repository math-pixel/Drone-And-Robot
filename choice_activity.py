import asyncio
from common import run_client

CLIENT_KEY = "choice_activity"

STEPS = [
    {"id": 1, "actions":[
        {"id": 1,"type": "video", "file": "chambre.mp4", "finished": False},
        {"id": 2,"type": "choice", "name": "Quel t-shirt vais-je porter aujourd'hui ?", "options": ["Classique", "Pokemon"], "chosen": -1},
        {"id": 3,"type": "video", "file": "bus.mp4", "finished": False},
        {"id": 4,"type": "choice", "name": "Une fois assis dans le bus, que fais-je ?", "options": ["Continuer à discuter", "Mettre mes écouteurs"], "chosen": -1},
        {"id": 5,"type": "video", "file": "classe.mp4", "finished": False},
        {"id": 6,"type": "choice", "name": "Au moment de devoir présenter l'exposé, que fais-je ?", "options": ["Passer plus tard et prendre l'aire", "Aller direct au tableaue"], "chosen": -1}
    ], "authorized": False, "finished": False},
    {"id": 2, "actions":[
        {"id": 1,"type": "video", "file": "remarque.mp4", "finished": False},
    ], "authorized": False, "finished": False},
    {"id": 3, "actions":[
        {"id": 1,"type": "video", "file": "recreation.mp4", "finished": False},
    ], "authorized": False, "finished": False},
]


if __name__ == "__main__":
    asyncio.run(run_client(CLIENT_KEY, STEPS))
