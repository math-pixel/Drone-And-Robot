import sys
import os
import asyncio

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.WSClient import WSClient
from utils.VideoPlayer import VideoPlayer

if __name__ == "__main__":

    STEPS = [
        {
            "id": 1,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_1_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_1_2_loop.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
                {"id": 4, "type": "video", "file": ["cine_1_4_choice_1.mp4", "cine_1_4_choice_2.mp4"], "finished": False},

                {"id": 5, "type": "video", "file": "cine_1_5.mp4", "finished": False},
                {"id": 6, "type": "video", "file": "cine_1_6_loop.mp4", "finished": False},
                {"id": 7, "type": "choice", "chosen": -1, "finished": False},
                {"id": 8, "type": "video", "file": ["cine_1_8_choice_1.mp4", "cine_1_8_choice_2.mp4"], "finished": False},

                {"id": 9, "type": "video", "file": "cine_1_9.mp4", "finished": False},
                {"id": 10, "type": "video", "file": "cine_1_10_loop.mp4", "finished": False},
                {"id": 11, "type": "choice", "chosen": -1, "finished": False},
                {"id": 12, "type": "video", "file": ["cine_1_12_choice_2.mp4","cine_1_12_choice_2.mp4"], "finished": False}, 
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 2,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_2_1.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 3,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_3_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_3_2_loop.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
                {"id": 4, "type": "video", "file": ["cine_3_4_choice_1.mp4", "cine_3_4_choice_2.mp4"], "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 4,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_4_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_4_2_loop.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 5,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_5_1_loop.mp4", "finished": False},
                {"id": 2, "type": "choice", "chosen": -1, "finished": False},
                {"id": 3, "type": "video", "file": "cine_5_3_choice_1.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
    ]

    # --- build videos dict once (keys = filenames used by player.play) ---
    videos = {}
    for step in STEPS:
        for a in step.get("actions", []):
            if a.get("type") != "video":
                continue
            f = a.get("file")
            files = f if isinstance(f, list) else [f]
            for name in files:
                if name:
                    videos[name] = f"./videos/{name}"

    # --- create player once ---
    player = VideoPlayer(fullscreen=True)
    player.load(videos)
    player.set_volume(80)

    # --- async wait helper using on_video_end ---
    _current = {"name": None, "event": None, "loop": None}

    def on_video_end(video_id: str):
        ev = _current.get("event")
        if ev is None:
            return
        if _current.get("name") != video_id:
            return
        loop = _current.get("loop")
        if loop is None:
            return
        loop.call_soon_threadsafe(ev.set)

    player.on_finished(on_video_end)

    async def play_and_wait(video_name: str):
        _current["loop"] = asyncio.get_running_loop()
        ev = asyncio.Event()
        _current["event"] = ev
        _current["name"] = video_name

        player.play(video_name)
        await ev.wait()

        _current["event"] = None
        _current["name"] = None

    def _get_step(step_id: int):
        return next((s for s in STEPS if s.get("id") == step_id), None)

    def _find_action_index(actions: list[dict], action: dict) -> int:
        for i, a in enumerate(actions):
            if a is action:
                return i
        aid = action.get("id")
        atype = action.get("type")
        for i, a in enumerate(actions):
            if a.get("id") == aid and a.get("type") == atype:
                return i
        return -1

    def pick_video_for_action(step_id: int, action: dict) -> str:
        file_field = action.get("file")

        # Simple string -> direct
        if not isinstance(file_field, list):
            return file_field

        # List -> pick using the choice JUST BEFORE this video in the same step
        step = _get_step(step_id)
        chosen = 0

        if step:
            actions = step.get("actions", [])
            idx = _find_action_index(actions, action)
            if idx != -1:
                for prev in reversed(actions[:idx]):
                    if prev.get("type") == "choice":
                        c = prev.get("chosen", -1)
                        if c in (0, 1):
                            chosen = c
                        else:
                            chosen = 0
                        break

        return file_field[min(chosen, len(file_field) - 1)]

    # ======================================================
    # DELEGATE
    # ======================================================

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_id = action.get("id")
        action_type = action.get("type")

        match action_type:
            case "video":
                file_name = pick_video_for_action(step_id, action)

                print(f"     🎥 Playing video: {file_name}")
                await play_and_wait(file_name)

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)

            case "choice":
                print("\n     ❓ CHOIX")
                selected = -1
                while selected not in (0, 1):
                    raw = input("     -> Tape 1 ou 2 : ").strip()
                    if raw == "1":
                        selected = 0
                    elif raw == "2":
                        selected = 1

                action["chosen"] = selected
                action["finished"] = True
                await client.send_choice_result(step_id, action_id, selected)

            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================

    client = WSClient(
        url="ws://192.168.1.13:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
