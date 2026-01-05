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
        print("Custom action handler")

    client = WSClient(
            url="ws://172.28.55.91:8057/ws",
            client_key="choice_activity",
            action_delegate=my_action_handler,
            steps=STEPS
        )
        
    asyncio.run(client.run())