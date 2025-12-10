# test_client.py
import asyncio
import websockets
import json

config = """
{
    "name": "global_data_transfer",
    "version": "1.0.0",
    "sequencing" : 1,
    "activity_atmosphere": {
        "ws_server_address": "ws://localhost:8765",
        "dmx": [
            {"lamp1": 
                {"channel": 1, "value": 255}
            },
            {"lamp2": 
                {"channel": 2, "value": 128}
            }
        ],
        "sound": {
            "file": "background_music.mp3",
            "volume": 0.8,
            "loop": true
        }
    },

    "activity_control": {
        "ws_server_address": "ws://",
        "difficulty_level": 1,
        "enable": false
    },

    "activity_oral": {
        "ws_server_address": "ws://",
        "difficulty_level": 1,
        "enable": false
    },

    "activity_knock_down": {
        "ws_server_address": "ws://",
        "difficulty_level": 1,
        "enable": false,
        "number_of_points_detected": 0,
        "rover_rotation_angle": 90
    },

    "activity_speak_to_mom": {
        "ws_server_address": "ws://",
        "difficulty_level": 1,
        "enable": false,
        "llm_model": "gpt-4",
        "llm_server_address": "http://"
    },

    "activity_monitoring": {
        "ws_server_address": "ws://",
        "emotions": [
            {
                "type": "happiness",
                "level": 0.7
            },
            {
                "type": "stress",
                "level": 0.3
            },
            {
                "type": "engagement",
                "level": 0.5
            }
        ]
    },

    "global_activity": {
        "ws_server_address": "ws://",
        "data": {},
        "step_of_activities": 0
    }
}
"""

async def ws_send_to(uri = "ws://localhost:8765", data="Salut serveur!"):
    uri = uri
    async with websockets.connect(uri) as websocket:
        # 1. Message normal
        await websocket.send("Salut serveur!")
        
        # 2. Le message spécial JSON
        data = data
        await websocket.send(json.dumps(data))
        
        # Lire la réponse du process
        response = await websocket.recv()
        print(f"Réponse du serveur: {response}")

if __name__ == "__main__":
    asyncio.run(ws_send_to(uri="ws://localhost:8765", data=json.loads(config)))