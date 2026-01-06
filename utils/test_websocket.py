import itertools
import random

if __name__ == "__main__":
    import asyncio
    from utils.WSClient import WSClient

    STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 1, "type": "video", "file": "classe.mp4", "finished": False},
                {"id": 2, "type": "choice", "chosen": -1, "name": "question ?", "options": [
                    {"id": 1, "text": "Passer plus tard"},
                    {"id": 2, "text": "Aller direct au tableau"}
                ], "finished": False}
            ], 
            "authorized": False, 
            "finished": False
        },
    ]

    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        keys = [
            "rover_stop",
            "rover_forward_10_1",
            "rover_forward_30_2",
            "rover_forward_60_3",
            "rover_backward_10_1",
            "rover_backward_40_2",
            "rover_backward_80_3",
            "rover_right_30",
            "rover_right_90",
            "rover_left_30",
            "rover_left_90",
            "rover_left_180",
            "rover_right_180",
        ]

        # 1er envoi pour démarrer
        first_key = random.choice(keys)
        await client._send_json(key=first_key)
        print(f"Sent: {first_key}")

        # Ensuite: à chaque Enter => prochaine key (en boucle)
        for k in itertools.cycle(keys):
            input("Press Enter to send next rover command...")
            await client._send_json(key=k)
            print(f"Sent: {k}")

    client = WSClient(
            url="ws://192.168.10.34:8057/ws",
            client_key="throw_activity",
            action_delegate=my_action_handler,
            steps=STEPS
        )
        
    asyncio.run(client.run())