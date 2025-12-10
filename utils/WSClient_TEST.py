# test_client.py
import asyncio
import websockets
import json

async def send_test():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # 1. Message normal
        await websocket.send("Salut serveur!")
        
        # 2. Le message spécial JSON
        data = {
            "name": "global_data_transfer",
            "payload": {
                "id": 123,
                "temperature": 25.5,
                "forward_to_remote": False
            }
        }
        await websocket.send(json.dumps(data))
        
        # Lire la réponse du process
        response = await websocket.recv()
        print(f"Réponse du serveur: {response}")

asyncio.run(send_test())