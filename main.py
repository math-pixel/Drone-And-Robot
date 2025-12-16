import asyncio
import json
import websockets

async def main():
    ws_url = input("WS server url (ex: ws://192.168.1.10:8085/ws): ").strip()

    async with websockets.connect(ws_url) as ws:
        raw = await ws.recv()
        print("Received from server:\n", raw)

        data = json.loads(raw)
        key = data.get("key", "")

        match key:
            case "identification_request":
                data["key"] = "identification_test_activity"

                if isinstance(data.get("activity"), list):
                    for obj in data["activity"]:
                        if "test_activity" in obj and isinstance(obj["test_activity"], dict):
                            obj["test_activity"]["ws_client_adress"] = ws_url
                            obj["test_activity"]["connected"] = False  # client state

                payload = json.dumps(data)
                await ws.send(payload)
                print("\nSent to server:\n", payload)

                # optional: receive updated global json broadcast from server
                try:
                    reply = await asyncio.wait_for(ws.recv(), timeout=2)
                    print("\nServer replied/broadcasted:\n", reply)
                except asyncio.TimeoutError:
                    pass

            case _:
                print(f"Unhandled key: {key}")

if __name__ == "__main__":
    asyncio.run(main())
