# mom_activity/main.py
if __name__ == "__main__":
    import asyncio
    import json
    import random
    from pathlib import Path

    from utils.WSClient import WSClient
    from mom_activity.keyword_listener_pty import KeywordSTT
    from utils.AudioPlayer import AudioPlayer  # adapte si ton fichier est ailleurs

    def strip_commas(s: str) -> str:
        return s.replace(",", "").replace("，", "")

    def score_to_angle(score: int, target: int = 100) -> int:
        score = max(0, min(target, score))
        return int(round((score / target) * 180.0))

    phrases_path = (Path(__file__).parent / "phrases.json").resolve()
    phrases = json.loads(phrases_path.read_text(encoding="utf-8"))

    POSITIVES = [strip_commas(x) for x in phrases.get("positives", [])]
    NEGATIVES = [strip_commas(x) for x in phrases.get("negatives", [])]

    INSTANT_WIN_PHRASES = [
        "Vive la maman de Mathias",
    ]
    INSTANT_WIN_PHRASES = [strip_commas(x) for x in INSTANT_WIN_PHRASES]
    INSTANT_WIN_SET = set(INSTANT_WIN_PHRASES)

    STEPS = [
        {
            "id": 1,
            "actions": [
                {
                    "id": 1,
                    "type": "keyword_score",
                    "positive_texts": POSITIVES,
                    "negative_texts": NEGATIVES,
                    "positive_delta": 10,
                    "negative_delta": -10,
                    "target_score": 100,
                    "score": 50,
                    "finished": False,
                }
            ],
            "authorized": False,
            "finished": False,
        },
    ]

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_id = int(action.get("id", -1))
        action_type = action.get("type")

        match action_type:
            case "keyword_score":
                positives = action.get("positive_texts") or []
                negatives = action.get("negative_texts") or []
                pos_delta = int(action.get("positive_delta", 10))
                neg_delta = int(action.get("negative_delta", -10))
                target = int(action.get("target_score", 100))

                action["score"] = int(action.get("score", 50))
                done = asyncio.Event()
                loop = asyncio.get_running_loop()

                stt_path = (Path(__file__).parent / "stt_from_mic_mlx.py").resolve()
                keywords = list(positives) + list(negatives) + list(INSTANT_WIN_SET)

                # ─────────────────────────────────────────────
                # AUDIO
                # ─────────────────────────────────────────────
                player = AudioPlayer()
                sounds_dir = "./audios/"

                player.load_multiple(
                    {
                        "bg": f"{sounds_dir}musique_de_fond.mp3",
                        "pos_1": f"{sounds_dir}positif_1.mp3",
                        "pos_2": f"{sounds_dir}positif_2.mp3",
                        "pos_3": f"{sounds_dir}positif_3.mp3",
                        "neg_1": f"{sounds_dir}negatif_1.mp3",
                        "neg_2": f"{sounds_dir}negatif_2.mp3",
                        "neg_3": f"{sounds_dir}negatif_3.mp3",
                    }
                )

                # Start background music when recording starts
                player.play("bg", volume=1.0, loop=True)

                # remember last chosen index so we mirror it on sign flip
                last_sfx_index: int | None = None

                def play_signed_sfx(is_positive: bool):
                    nonlocal last_sfx_index
                    if last_sfx_index is None:
                        last_sfx_index = random.randint(1, 3)

                    name = (f"pos_{last_sfx_index}" if is_positive else f"neg_{last_sfx_index}")
                    player.play(name, volume=1.0, loop=False)

                    # next time we stay same sign, we can choose a new random
                    # (but if sign flips, we reuse last_sfx_index)
                    return

                def next_index():
                    nonlocal last_sfx_index
                    last_sfx_index = random.randint(1, 3)

                # ─────────────────────────────────────────────
                # STEPPER KEY INIT
                # ─────────────────────────────────────────────
                # initial_angle = score_to_angle(action["score"], target)
                # await client._send_json(key=f"{client.client_key}_stepper_{initial_angle}")

                last_sign: str | None = None  # "pos" or "neg"

                def on_kw(raw_kw: str):
                    nonlocal last_sign

                    kw = strip_commas(raw_kw)
                    if kw in INSTANT_WIN_SET:
                        action["score"] = target
                        angle = score_to_angle(target, target)
                        loop.create_task(client._send_json(key=f"{client.client_key}_stepper_{angle}"))
                        player.stop("bg")
                        done.set()
                        return
                    is_positive = kw in positives

                    delta = pos_delta if is_positive else neg_delta
                    current = int(action.get("score", 50))
                    new_score = current + delta

                    if new_score < 0:
                        new_score = 0

                    action["score"] = new_score

                    # ── SFX rule:
                    # - choose random index when sign is same as previous or first time
                    # - if sign flips, reuse the previous index but with opposite prefix
                    current_sign = "pos" if is_positive else "neg"
                    if last_sign is None:
                        next_index()
                        play_signed_sfx(is_positive)
                    elif current_sign == last_sign:
                        next_index()
                        play_signed_sfx(is_positive)
                    else:
                        # sign flipped -> keep same index, just swap pos/neg
                        play_signed_sfx(is_positive)

                    last_sign = current_sign

                    angle = score_to_angle(new_score, target)
                    loop.create_task(client._send_json(key=f"{client.client_key}_stepper_{angle}"))

                    sign = "+" if delta >= 0 else ""
                    label = "POSITIVE" if delta > 0 else "NEGATIVE"
                    print(f"\n🎙️ {label} {sign}{delta} → {new_score}/{target} | angle={angle}\n")

                    if new_score >= target:
                        player.stop("bg")
                        done.set()

                stt = KeywordSTT(
                    stt_script=str(stt_path),
                    keywords=keywords,
                    on_keyword=on_kw,
                )

                stt.start()
                try:
                    await done.wait()
                finally:
                    stt.stop()
                    player.stop_all()
                    player.close()

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)

            case _:
                print(f"⚠️ Unknown action type: {action_type}")

    async def my_key_handler(data: dict, client: WSClient):
        pass

    client = WSClient(
        url="ws://192.168.10.34:8057/ws",
        client_key="mom_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,
        steps=STEPS,
    )

    asyncio.run(client.run())
