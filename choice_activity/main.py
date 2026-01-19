import sys
import os
import asyncio
import time
import numpy as np
import contextlib

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.MicrophoneLevelMeter import MicrophoneLevelMeter, LevelConfig
from utils.WSClient import WSClient
from utils.rpi.Bouton import Bouton
from utils.VideoPlayer import VideoPlayer

# ======================================================
# CONFIGURATION DES BOUTONS
# ======================================================

idButtonPressed: str | None = None

btnLeft = Bouton(pin=17, pull_up=True, long_press_time=2.0)
btnRight = Bouton(pin=27, pull_up=True, long_press_time=2.0)

def signal_button_press(btn_id: str):
    global idButtonPressed
    print(f"👉 Hardware: Bouton {btn_id} appuyé")
    idButtonPressed = btn_id

btnLeft.on_press = lambda: signal_button_press("left")
btnRight.on_press = lambda: signal_button_press("right")

def on_release_feedback(duration: float):
    print(f"   (Relâché après {duration:.2f}s)")

btnLeft.on_release = on_release_feedback
btnRight.on_release = on_release_feedback


if __name__ == "__main__":

    STEPS = [
        {
            "id": 1,
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
                {"id": 4, "type": "video", "file": ["cine_6_4_choice_1.mp4", "cine_6_4_choice_2.mp4"], "finished": False},
                {"id": 5, "type": "video", "file": "cine_6_5_loop.mp4", "finished": False},
                {"id": 6, "type": "choice", "chosen": -1, "finished": False},
                {"id": 7, "type": "video", "file": ["cine_6_7_choice_1.mp4", "cine_6_7_choice_2.mp4"], "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
    ]

    # ======================================================
    # VIDEOS
    # ======================================================

    video_prefix = ""

    def apply_prefix(name: str) -> str:
        return f"{video_prefix}{name}" if video_prefix else name

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
                    videos[f"vert{name}"] = f"./videos/vert{name}"

    player = VideoPlayer(fullscreen=True)
    player.load(videos)
    player.set_volume(80)

    meter = MicrophoneLevelMeter(LevelConfig())

    # ======================================================
    # MICRO -> WS (crie)
    # ======================================================

    async def _ws_send(client: WSClient, payload: dict) -> None:
        if hasattr(client, "send_data"):
            await client.send_data(payload)
            return
        if hasattr(client, "_send_json"):
            client.data = payload  # type: ignore[attr-defined]
            await client._send_json(payload.get("key"))  # type: ignore[attr-defined]
            return
        raise AttributeError("WSClient: aucune méthode send_data/_send_json trouvée")

    async def _stream_crie(client: WSClient, countdown_s: float = 14.0, poll_s: float = 0.1) -> None:
        t0 = time.monotonic()
        samples: list[float] = []

        while True:
            if (time.monotonic() - t0) >= countdown_s:
                break
            samples.append(meter.get_db())
            await asyncio.sleep(poll_s)

        base = float(np.percentile(samples, 90)) if samples else meter.get_db()
        margin_db = 10.0
        gate_db = base + margin_db

        print(f"🔇 Calibration done ({countdown_s:.0f}s): ambient≈{base:.1f} dB, gate≈{gate_db:.1f} dB")

        last = 0
        while True:
            db = meter.get_db()
            if db < gate_db:
                last = 0
                await asyncio.sleep(poll_s)
                continue

            lvl = meter.get_level_0_to_5()
            if 1 <= lvl <= 5 and lvl != last:
                await _ws_send(client, {"key": f"crie_{lvl}", "level": lvl, "db": db, "gate_db": gate_db})
                last = lvl

            await asyncio.sleep(poll_s)

    # ======================================================
    # PLAYER WAIT
    # ======================================================

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

    async def play_and_wait(video_name: str):
        _current["loop"] = asyncio.get_running_loop()
        ev = asyncio.Event()
        _current["event"] = ev
        _current["name"] = video_name

        player.play(video_name)
        await ev.wait()

        _current["event"] = None
        _current["name"] = None

    async def _play_loop_in_background(video_name: str) -> asyncio.Task:
        stop_loop_event.clear()

        async def _runner():
            while not stop_loop_event.is_set():
                await play_and_wait(video_name)

        return asyncio.create_task(_runner())

    # ======================================================
    # HELPERS
    # ======================================================

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

        if chosen == 0 and len(file_field) == 1:
            return None

        return apply_prefix(file_field[min(chosen, len(file_field) - 1)])

    def is_loop_video(name: str) -> bool:
        n = os.path.basename(name)
        return n.endswith("_loop.mp4") or n.endswith("_loop")

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

    async def wait_for_button_choice() -> int:
        global idButtonPressed
        idButtonPressed = None
        while idButtonPressed is None:
            await asyncio.sleep(0.02)

        if idButtonPressed == "left":
            return 0
        if idButtonPressed == "right":
            return 1
        return 0

    # ======================================================
    # DELEGATE
    # ======================================================

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        global idButtonPressed, video_prefix

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
                    _ = await _play_loop_in_background(file_name)
                    action["finished"] = True
                    await client.send_action_finished(step_id, action_id)
                    return

                # ---- SPECIAL: Scene du cri ----
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

                # ---- SPECIAL: Loop standard (attente bouton pour passer à la suite) ----
                elif is_loop_video(file_name):
                    print(f"     🔄 Loop '{file_name}' en cours (attente bouton ou event)...")
                    
                    # On s'assure que l'état du bouton est vierge avant de commencer
                    idButtonPressed = None 

                    # On boucle tant que : Pas de bouton pressé ET Pas d'événement de stop externe
                    while idButtonPressed is None and not stop_loop_event.is_set():
                        
                        # --- Début manuel de play_and_wait ---
                        # On le fait manuellement pour pouvoir interrompre l'attente (sleep)
                        _current["loop"] = asyncio.get_running_loop()
                        ev = asyncio.Event()
                        _current["event"] = ev
                        _current["name"] = file_name
                        
                        player.play(file_name)

                        # Boucle d'attente active
                        while not ev.is_set():
                            # 1. Vérifie si on a appuyé sur un bouton
                            if idButtonPressed is not None:
                                print(f"     ⏩ Bouton '{idButtonPressed}' détecté pendant le loop ! Passage à la suite.")
                                break # Sort du while d'attente vidéo
                            
                            # 2. Vérifie si un event externe demande l'arrêt
                            if stop_loop_event.is_set():
                                break # Sort du while d'attente vidéo
                            
                            await asyncio.sleep(0.05) # Petite pause pour ne pas bloquer le CPU

                        # --- Fin manuelle de play_and_wait ---
                        _current["event"] = None
                        _current["name"] = None
                        
                    # Ici, on est sorti de la boucle while principale, donc soit bouton, soit stop_event
                    # La vidéo suivante va pouvoir se lancer.

                # ---- CAS CLASSIQUE ----
                else:
                    await play_and_wait(file_name)

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)

            case "choice":
                print("\n     ❓ CHOIX")
                print("     👉 Appuyez sur GAUCHE (left) ou DROITE (right)")

                selected = await wait_for_button_choice()

                stop_loop_event.set()

                action["chosen"] = selected
                action["finished"] = True

                if step_id == 2 and action_id == 3:
                    video_prefix = "vert" if selected == 1 else ""

                print("     ✅ Sélection :", "GAUCHE" if selected == 0 else "DROITE")
                await client.send_choice_result(step_id, action_id, selected)

            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================

    client = WSClient(
        url="ws://192.168.10.123:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
    finally:
        btnLeft.cleanup()
        btnRight.cleanup()
