# mom_activity/main.py
if __name__ == "__main__":
    import asyncio
    import json
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
                keywords = list(positives) + list(negatives)

                # ─────────────────────────────────────────────
                # AUDIO
                # ─────────────────────────────────────────────
                player = AudioPlayer()
                sounds_dir = "./audios/"

                player.load_multiple(
                    {
                        "bg": f"{sounds_dir}musique_de_fond.mp3",
                        "pos": f"{sounds_dir}curseur_positif.mp3",
                        "neg": f"{sounds_dir}curseur_negatif.mp3",
                    }
                )

                # Start background music when recording starts
                player.play("bg", volume=1.0, loop=True)

                # ─────────────────────────────────────────────
                # STEPPER KEY INIT
                # ─────────────────────────────────────────────
                initial_angle = score_to_angle(action["score"], target)
                await client._send_json(key=f"{client.client_key}_stepper_{initial_angle}")

                def on_kw(raw_kw: str):
                    kw = strip_commas(raw_kw)

                    is_positive = kw in positives
                    delta = pos_delta if is_positive else neg_delta

                    current = int(action.get("score", 50))
                    new_score = current + delta

                    # score min = 0
                    if new_score < 0:
                        new_score = 0

                    action["score"] = new_score

                    # play SFX
                    if is_positive:
                        player.play("pos", volume=1.0, loop=False)
                    else:
                        player.play("neg", volume=1.0, loop=False)

                    angle = score_to_angle(new_score, target)
                    loop.create_task(client._send_json(key=f"{client.client_key}_stepper_{angle}"))

                    sign = "+" if delta >= 0 else ""
                    label = "POSITIVE" if delta > 0 else "NEGATIVE"
                    print(f"\n🎙️ {label} {sign}{delta} → {new_score}/{target} | angle={angle}\n")

                    if new_score >= target:
                        # stop background music when score reaches 100
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
