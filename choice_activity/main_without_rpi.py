import sys
import os
import asyncio

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

import time
import numpy as np

from utils.WSClient import WSClient
from utils.VideoPlayer import VideoPlayer

import contextlib
import inspect

from utils.MicrophoneLevelMeter import MicrophoneLevelMeter, LevelConfig
# ✅ REMPLACE ta classe ChoiceListener par celle-ci (1/2 sans ENTER + stop loop dès le choix)

import os
import sys
import tty
import termios

class ChoiceListener:
    def __init__(self, stop_loop_event: asyncio.Event):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._event = asyncio.Event()
        self._pending: int | None = None
        self._stop_loop_event = stop_loop_event

        self._fd = sys.stdin.fileno()
        self._old_term: list[int] | None = None

    def start(self):
        self._loop = asyncio.get_running_loop()

        # mode "cbreak" => on lit les touches sans ENTER
        self._old_term = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

        self._loop.add_reader(self._fd, self._on_stdin)

    def stop(self):
        if self._loop is not None:
            self._loop.remove_reader(self._fd)
            self._loop = None

        if self._old_term is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_term)
            self._old_term = None

    def _on_stdin(self):
        try:
            b = os.read(self._fd, 1)  # 1 char
        except Exception:
            return
        if not b:
            return

        ch = b.decode(errors="ignore")
        if ch == "1":
            self._pending = 0
            self._stop_loop_event.set()     # ✅ stop la video loop en cours
            self._event.set()
        elif ch == "2":
            self._pending = 1
            self._stop_loop_event.set()     # ✅ stop la video loop en cours
            self._event.set()

    def has_choice(self) -> bool:
        return self._event.is_set()

    async def wait_choice(self) -> int:
        await self._event.wait()
        val = 0 if self._pending is None else self._pending
        self._pending = None
        self._event.clear()
        self._stop_loop_event.clear()        # prêt pour un prochain loop
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
                {"id": 12, "type": "video", "file": ["cine_2_12_choice_2.mp4"], "finished": False}, 
                {"id": 13, "type": "video", "file": "cine_2_13_loop.mp4", "finished": False},
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

    meter = MicrophoneLevelMeter(LevelConfig())

    async def _ws_send(client: WSClient, payload: dict) -> None:
        # ✅ ton WSClient a cette méthode
        if hasattr(client, "send_data"):
            await client.send_data(payload)
            return

        # ✅ fallback (si un jour tu changes de client)
        if hasattr(client, "_send_json"):
            client.data = payload  # type: ignore[attr-defined]
            await client._send_json(payload.get("key"))  # type: ignore[attr-defined]
            return

        raise AttributeError("WSClient: aucune méthode send_data/_send_json trouvée")

    async def _stream_crie(client: WSClient, countdown_s: float = 14.0, poll_s: float = 0.1) -> None:
        # 1) Countdown + calibration du bruit ambiant (on n'envoie rien)
        t0 = time.monotonic()
        samples: list[float] = []

        while True:
            elapsed = time.monotonic() - t0
            if elapsed >= countdown_s:
                break

            # on "set le 0 sonore" => on ignore totalement l'envoi pendant le countdown
            samples.append(meter.get_db())
            await asyncio.sleep(poll_s)

        # 2) Déduire un seuil basé sur l'ambiance
        # base = percentile 90 du bruit ambiant (évite les pics) + marge
        base = float(np.percentile(samples, 90)) if samples else meter.get_db()
        margin_db = 10.0  # ↑ augmente si tu veux qu'il faille crier plus fort
        gate_db = base + margin_db

        print(f"🔇 Calibration done ({countdown_s:.0f}s): ambient≈{base:.1f} dB, gate≈{gate_db:.1f} dB")

        # 3) On envoie crie_x seulement si on dépasse gate_db
        last = 0
        while True:
            db = meter.get_db()
            if db < gate_db:
                last = 0
                await asyncio.sleep(poll_s)
                continue

            lvl = meter.get_level_0_to_5()  # 0..5
            if 1 <= lvl <= 5 and lvl != last:
                await _ws_send(client, {"key": f"crie_{lvl}", "level": lvl, "db": db, "gate_db": gate_db})
                last = lvl

            await asyncio.sleep(poll_s)



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
    choice_listener = ChoiceListener(stop_loop_event)

    def _is_loop_action(action: dict) -> bool:
        if action.get("type") != "video":
            return False
        f = action.get("file")
        if isinstance(f, list):
            return False
        return isinstance(f, str) and f.endswith("_loop.mp4")

    def _is_last_action_of_step(step_id: int, action: dict) -> bool:
        step = _get_step(step_id)
        if not step:
            return False
        actions = step.get("actions", [])
        idx = _find_action_index(actions, action)
        return idx != -1 and idx == (len(actions) - 1)

    async def _play_loop_in_background(video_name: str) -> asyncio.Task:
        stop_loop_event.clear()

        async def _runner():
            while not stop_loop_event.is_set():
                await play_and_wait(video_name)

        return asyncio.create_task(_runner())

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
    
    video_prefix = ""  # "" ou "vert"

    def apply_prefix(name: str) -> str:
        return f"{video_prefix}{name}" if video_prefix else name

    def pick_video_for_action(step_id: int, action: dict) -> str | None:
        file_field = action.get("file")

        if not isinstance(file_field, list):
            return apply_prefix(file_field)

        chosen = 0
        step = _get_step(step_id)
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

        # ✅ cas: seulement une vidéo (choice 2), et on a choisi 1 => pas de vidéo
        if chosen == 0 and len(file_field) == 1:
            return None

        return apply_prefix(file_field[min(chosen, len(file_field) - 1)])

    def is_loop_video(name: str) -> bool:
        return name.endswith("_loop.mp4") or name.endswith("_loop")

    server_interrupt = asyncio.Event()

    async def my_key_handler(data: dict, client: WSClient):
        server_interrupt.set()

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_id = action.get("id")
        action_type = action.get("type")

        match action_type:
            case "video":
                file_name = pick_video_for_action(step_id, action)
                if not file_name:
                    action["finished"] = True
                    await client.send_action_finished(step_id, action_id)
                    return

                print(f"     🎥 Playing video: {file_name}")

                # ---- SPECIAL: dernière action loop => on considère fini dès le lancement ----
                if _is_loop_action(action) and _is_last_action_of_step(step_id, action):
                    _ = await _play_loop_in_background(file_name)  # on la laisse tourner
                    action["finished"] = True
                    await client.send_action_finished(step_id, action_id)
                    return  # ✅ permet au WSClient d'envoyer step_finished juste après

                # ---- ton cas crie ----
                if file_name == "cine_5_2.mp4":
                    meter.start()
                    crie_task = asyncio.create_task(_stream_crie(client, countdown_s=14.0))
                    try:
                        await play_and_wait(file_name)
                    finally:
                        crie_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await crie_task
                        meter.stop()
                else:
                    if file_name.endswith("_loop.mp4"):
                        stop_loop_event.clear()
                        while not stop_loop_event.is_set():
                            await play_and_wait(file_name)
                    else:
                        await play_and_wait(file_name)

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)


            case "choice":
                stop_loop_event.clear()
                if not choice_listener.has_choice():
                    print("\n     ❓ CHOIX")
                    print("     -> Tape 1 (gauche) ou 2 (droite)")

                selected = await choice_listener.wait_choice()
                action["chosen"] = selected
                action["finished"] = True
                await client.send_choice_result(step_id, action_id, selected)

            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    async def main():
        choice_listener.start()
        client = WSClient(
            url="ws://192.168.10.123:8057/ws",
            client_key="choice_activity",
            action_delegate=my_action_handler,
            key_delegate=my_key_handler,
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
