import asyncio
import json
import websockets

async def run_client(ws_url: str, client_key: str, steps: list[dict]):
    input(f"Press Enter to connect to {ws_url}...")

    async with websockets.connect(ws_url) as ws:
        # --- Receive initial JSON ---
        raw = await ws.recv()
        data = json.loads(raw)

        print("\n📥 Initial key:", data.get("key"))

        if data.get("key") == "identification_request":
            data = handle_identification(data, client_key, steps)
            await send_json(ws, data, f"identification_{client_key}")

        # --- Interactive steps ---
        await handle_steps(ws, data, client_key)

        # --- Keep alive ---
        print("\n✅ All steps done. Waiting for server messages (Ctrl+C to exit)\n")
        try:
            while True:
                msg = await ws.recv()
                print("\n📥 Received:", json.loads(msg).get("key"))
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")

def handle_identification(data: dict, client_key: str, steps: list[dict]) -> dict:
    data["key"] = f"identification_{client_key}"

    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            activity = wrapper[client_key]
            activity["connected"] = True
            activity["step"] = steps
            print(f"✅ {client_key} activated with {len(steps)} steps")
            break
    else:
        print(f"⚠️ Activity '{client_key}' not found")

    return data

async def handle_steps(ws, data: dict, client_key: str):
    activity = find_activity(data, client_key)
    if not activity:
        return

    steps = activity.get("step", [])

    for index, step in enumerate(steps, start=1):
        input(f"\n➡️ Press Enter to complete step {index}: {step['name']}")

        step["finished"] = True
        data["key"] = f"{client_key}_activity_finished_step_{index}"

        await send_json(ws, data, data["key"])


def find_activity(data: dict, client_key: str) -> dict | None:
    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            return wrapper[client_key]
    return None

async def send_json(ws, data: dict, label: str):
    payload = json.dumps(data)
    await ws.send(payload)
    print(f"📤 Sent → {label}")
