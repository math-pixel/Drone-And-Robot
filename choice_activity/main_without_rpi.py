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


class ChoiceListener:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._event = asyncio.Event()
        self._pending: int | None = None

    def start(self):
        self._loop = asyncio.get_running_loop()
        self._loop.add_reader(sys.stdin, self._on_stdin)

    def stop(self):
        if self._loop is not None:
            self._loop.remove_reader(sys.stdin)
            self._loop = None

    def _on_stdin(self):
        line = sys.stdin.readline()
        if not line:
            return
        raw = line.strip()
        if raw == "1":
            self._pending = 0
            self._event.set()
        elif raw == "2":
            self._pending = 1
            self._event.set()

    def has_choice(self) -> bool:
        return self._event.is_set()

    async def wait_choice(self) -> int:
        await self._event.wait()
        val = 0 if self._pending is None else self._pending
        self._pending = None
        self._event.clear()
        return val


if __name__ == "__main__":

    STEPS = [
        {
            "id":1,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_1_1_loop.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_1_2.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 2,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_2_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_2_2_loop.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
                {"id": 4, "type": "video", "file": ["cine_2_4_choice_1.mp4", "cine_2_4_choice_2.mp4"], "finished": False},

                {"id": 5, "type": "video", "file": "cine_2_5.mp4", "finished": False},
                {"id": 6, "type": "video", "file": "cine_2_6_loop.mp4", "finished": False},
                {"id": 7, "type": "choice", "chosen": -1, "finished": False},
                {"id": 8, "type": "video", "file": ["cine_2_8_choice_1.mp4", "cine_2_8_choice_2.mp4"], "finished": False},

                {"id": 9, "type": "video", "file": "cine_2_9.mp4", "finished": False},
                {"id": 10, "type": "video", "file": "cine_2_10_loop.mp4", "finished": False},
                {"id": 11, "type": "choice", "chosen": -1, "finished": False},
                {"id": 12, "type": "video", "file": ["cine_2_12_choice_2.mp4","cine_2_12_choice_2.mp4"], "finished": False}, 
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 3,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_3_1_loop.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_3_2.mp4", "finished": False},
                {"id": 3, "type": "video", "file": "cine_3_3_loop.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 4,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_4_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_4_2.mp4", "finished": False},
                {"id": 3, "type": "video", "file": "cine_4_3_loop.mp4", "finished": False},
                {"id": 4, "type": "choice", "chosen": -1, "finished": False},
                {"id": 5, "type": "video", "file": ["cine_4_5_choice_1.mp4", "cine_4_5_choice_2.mp4"], "finished": False},
                {"id": 6, "type": "video", "file": "cine_4_6_loop.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 5,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_5_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_5_2.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 6,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_6_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_6_2_loop.mp4", "finished": False},
                {"id": 3, "type": "choice", "chosen": -1, "finished": False},
                {"id": 4, "type": "video", "file": ["cine_6_4_choice_1.mp4","cine_6_4_choice_2.mp4"], "finished": False},
                {"id": 5, "type": "video", "file": "cine_6_5_loop.mp4", "finished": False},
                {"id": 6, "type": "choice", "chosen": -1, "finished": False},
                {"id": 7, "type": "video", "file": ["cine_6_7_choice_1.mp4","cine_6_7_choice_2.mp4"], "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
    ]

    videos: dict[str, str] = {}
    for step in STEPS:
        for a in step.get("actions", []):
            if a.get("type") != "video":
                continue
            f = a.get("file")
            files = f if isinstance(f, list) else [f]
            for name in files:
                if name:
                    videos[name] = f"./videos/{name}"

    player = VideoPlayer(fullscreen=True)
    player.load(videos)
    player.set_volume(80)

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

    stop_loop_event = asyncio.Event()

    def _on_any_keypress():
        # terminal = line buffered -> il faudra ENTER, mais ça suffit pour tester
        sys.stdin.readline()
        stop_loop_event.set()

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
        if not isinstance(file_field, list):
            return file_field

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
                        break

        return file_field[min(chosen, len(file_field) - 1)]

    def is_loop_video(name: str) -> bool:
        return name.endswith("_loop.mp4") or name.endswith("_loop")

    choice_listener = ChoiceListener()
    server_interrupt = asyncio.Event()

    async def my_key_handler(data: dict, client: WSClient):
        server_interrupt.set()

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_id = action.get("id")
        action_type = action.get("type")

        match action_type:
            case "video":
                file_name = pick_video_for_action(step_id, action)
                print(f"     🎥 Playing video: {file_name}")

                if file_name.endswith("_loop.mp4"):
                    stop_loop_event.clear()

                    loop = asyncio.get_running_loop()
                    loop.add_reader(sys.stdin, _on_any_keypress)
                    try:
                        while not stop_loop_event.is_set():
                            await play_and_wait(file_name)
                    finally:
                        loop.remove_reader(sys.stdin)
                else:
                    await play_and_wait(file_name)

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)

            case "choice":
                stop_loop_event.clear()
                if not choice_listener.has_choice():
                    print("\n     ❓ CHOIX")
                    print("     -> Tape 1 (gauche) ou 2 (droite) puis ENTER")

                selected = await choice_listener.wait_choice()
                action["chosen"] = selected
                action["finished"] = True

                await client.send_choice_result(step_id, action_id, selected)

            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    async def main():
        choice_listener.start()

        client = WSClient(
            url="ws://192.168.10.34:8057/ws",
            client_key="choice_activity",
            action_delegate=my_action_handler,
            key_delegate=my_key_handler,  # si ton WSClient n'a pas ça, dis-moi sa signature et je l'adapte
            steps=STEPS
        )

        try:
            await client.run()
        finally:
            choice_listener.stop()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
