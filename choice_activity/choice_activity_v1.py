import asyncio
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
    # DELEGATE (à personnaliser par l'utilisateur)
    # ======================================================
    
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        """
        Delegate personnalisé pour gérer les actions.
        L'utilisateur implémente ici son match case.
        """
        action_id = action.get("id")
        action_type = action.get("type")
        
        match action_type:
            case "video":
                file = action.get("file")
                print(f"     🎥 Playing video: {file}")
                
                # Simulation: attendre que la vidéo soit "jouée"
                input(f"     ⏸️  Press Enter when video '{file}' is finished...")
                
                # Marquer comme terminé
                action["finished"] = True
                await client.send_action_finished(step_id, action_id)
                
            case "choice":
                name = action.get("name")
                options = action.get("options", [])
                
                print(f"     ❓ {name}")
                for i, opt in enumerate(options):
                    print(f"        [{i}] {opt}")
                
                # Attendre le choix
                selected = -1
                while selected not in range(len(options)):
                    try:
                        selected = int(input("     👉 Your choice: "))
                    except ValueError:
                        print("     ⚠️  Invalid input")
                
                # Enregistrer le choix
                action["chosen"] = selected
                await client.send_choice_result(step_id, action_id, selected)
                
            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================
    
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    
    asyncio.run(client.run())