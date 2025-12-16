import asyncio
import json
import websockets

async def main():
    ws_url = "ws://192.168.1.13:8057/ws"
    input(f"Press Enter to connect to {ws_url}...")

    async with websockets.connect(ws_url) as ws:
        raw = await ws.recv()

        data = json.loads(raw)
        key = data.get("key", "")
        print(f"\nProcessing key: {key}")

        match key:
            case "identification_request":
                data["key"] = "identification_test_activity"
                print(data["key"])

                payload = json.dumps(data)
                await ws.send(payload)

                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=2)
                    json_reply = json.loads(reply)
                    print("\nServer replied/broadcasted:\n", json_reply["key"])
                except asyncio.TimeoutError:
                    pass

            case _:
                print(f"Unhandled key: {key}")

        # 🔒 GARDER LA CONNEXION OUVERTE
        print("\n✅ Connected. Press Ctrl+C to exit.\n")
        try:
            while True:
                msg = await ws.recv()
                json_msg = json.loads(msg)
                print("\n📥 Received:\n", json_msg["key"])
        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")

if __name__ == "__main__":
    asyncio.run(main())
