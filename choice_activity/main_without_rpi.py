import sys
import os
import asyncio

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.WSClient import WSClient

if __name__ == "__main__":

    # Définition des steps
    STEPS = [
        {
            "id": 1,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_1_1.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_1_2_loop.mp4", "finished": False},
                {"id": 4, "type": "video", "file": "cine_1_4_choice_1.mp4", "finished": False},
                {"id": 4, "type": "video", "file": "cine_1_4_choice_2.mp4", "finished": False},
                {"id": 5, "type": "video", "file": "cine_1_5.mp4", "finished": False},
                {"id": 6, "type": "video", "file": "cine_1_6_loop.mp4", "finished": False},
                {"id": 8, "type": "video", "file": "cine_1_8_choice_1.mp4", "finished": False},
                {"id": 8, "type": "video", "file": "cine_1_8_choice_2.mp4", "finished": False},
                {"id": 9, "type": "video", "file": "cine_1_9.mp4", "finished": False},
                {"id": 10, "type": "video", "file": "cine_1_10_loop.mp4", "finished": False},
                {"id": 12, "type": "video", "file": "cine_1_12_choice_2.mp4", "finished": False},
                {"id": 12, "type": "video", "file": "vert_cine_1_12_choice_2.mp4", "finished": False},
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
                {"id": 4, "type": "video", "file": "cine_3_4_choice_1.mp4", "finished": False},
                {"id": 4, "type": "video", "file": "cine_3_4_choice_2.mp4", "finished": False},
                {"id": 5, "type": "video", "file": "cine_3_5.mp4", "finished": False},
                {"id": 6, "type": "video", "file": "cine_3_6_loop.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
        {
            "id": 4,
            "actions": [
                {"id": 1, "type": "video", "file": "cine_4_1_loop.mp4", "finished": False},
                {"id": 2, "type": "video", "file": "cine_4_2_choice_1.mp4", "finished": False},
            ],
            "authorized": False,
            "finished": False
        },
    ]

    # ======================================================
    # DELEGATE
    # ======================================================

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        action_id = action.get("id")
        action_type = action.get("type")

        player = VideoPlayer(fullscreen=True)

        player.load(
            {
                "intro": "./utils/choix_tshirt.mp4",
            }
        )

        def on_video_end(video_id: str):
            print(f"✓ Vidéo '{video_id}' terminée!")
            if video_id == "intro":
                player.play("presentation")
            elif video_id == "presentation":
                player.play("credits")

        player.on_finished(on_video_end)
        player.set_volume(80)
        player.play("intro")

        match action_type:
            case "video":
                file_name = action.get("file")
                print(f"     🎥 Playing video: {file_name}")

                player.play(file_name)

                action["finished"] = True
                await client.send_action_finished(step_id, action_id)

            case "choice":
                name = action.get("name")
                options = action.get("options", [])

                print(f"\n     ❓ CHOIX : {name}")
                print(f"     1) {options[0]['text'] if len(options) > 0 else 'Option 1'}")
                print(f"     2) {options[1]['text'] if len(options) > 1 else 'Option 2'}")

                selected = -1
                while selected not in (0, 1):
                    raw = input("     -> Tape 1 ou 2 : ").strip()
                    if raw == "1":
                        selected = 0
                    elif raw == "2":
                        selected = 1

                action["chosen"] = selected
                await client.send_choice_result(step_id, action_id, selected)

            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================

    client = WSClient(
        url="ws://192.168.10.34:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
