import asyncio
import json
import websockets

WS_URL = "ws://192.168.10.182:8057/ws"

async def run_client(client_key: str, items: list[dict] | None = None):
    input(f"Press Enter to connect to {WS_URL}...")

    async with websockets.connect(WS_URL) as ws:
        raw = await ws.recv()
        data = json.loads(raw)

        print("\n📥 Initial key:", data.get("key"))

        if data.get("key") == "identification_request":
            data, mode = handle_identification(data, client_key, items)
            await send_json(ws, data, f"identification_{client_key}")

            if mode == "step":
                print("⏳ Waiting for start_authorization...")
                await wait_for_authorization(ws)
                await handle_steps(ws, data, client_key)

            elif mode == "choices":
                await handle_choices(ws, data, client_key)

        print("\n✅ Client ready. Waiting for server (Ctrl+C to exit)\n")
        try:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                key = data.get("key")

                if key == "update_emotions":
                    print("\n🎭 Emotions update new value:")
                    for emo in data.get("emotions", []):
                        print(f"  - {emo.get('type')}: {emo.get('level')}")
                else:
                    print("\n📥 Received:", key)

        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")


def handle_identification(data: dict, client_key: str, items: list[dict]):
    data["key"] = f"identification_{client_key}"

    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            activity = wrapper[client_key]
            activity["connected"] = True

            if "step" in activity:
                activity["step"] = items
                mode = "step"
            elif "choices" in activity:
                activity["choices"] = items
                mode = "choices"
            else:
                mode = "unknown"

            print(f"✅ {client_key} activated ({mode})")
            return data, mode

    print(f"⚠️ Activity '{client_key}' not found")
    return data, None


async def handle_steps(ws, data: dict, client_key: str):
    activity = find_activity(data, client_key)
    steps = activity.get("step", [])

    for index, step in enumerate(steps, start=1):
        input(f"\n➡️ Press Enter to finish step {index}: {step['name']}")

        step["finished"] = True
        data["key"] = f"{client_key}_finished_step_{index}"

        await send_json(ws, data, data["key"])

    activity["finished"] = True
    data["key"] = f"{client_key}_finished"

    print(f"\n🏁 {client_key} finished")

    await send_json(ws, data, data["key"])


async def handle_choices(ws, data: dict, client_key: str):
    activity = find_activity(data, client_key)
    choices = activity.get("choices", [])

    for index, choice in enumerate(choices, start=1):

        # 🔐 À partir du choix 2 → autorisation requise
        if index > 1:
            print(f"\n⏳ Waiting authorization for choice {choice['id']}...")
            await wait_for_choice_authorization(ws, choice["id"])

        print(f"\n🔘 Choice {choice['id']}: {choice['name']}")
        for i, opt in enumerate(choice.get("options", [])):
            print(f"  {i}: {opt}")

        selected = None
        while selected not in (0, 1):
            try:
                selected = int(input("➡️ Choose 0 or 1: "))
            except ValueError:
                pass

        choice["chosen"] = selected
        data["key"] = f"{client_key}_{choice['id']}_{selected}"

        await send_json(ws, data, data["key"])

    print("\n🏁 All choices completed")

async def wait_for_choice_authorization(ws, choice_id: str):
    expected_key = f"choice_{choice_id}_authorization"

    while True:
        msg = await ws.recv()
        data = json.loads(msg)
        key = data.get("key")

        if key == expected_key:
            print(f"✅ Authorization received for choice {choice_id}")
            return

        elif key == "update_emotions":
            print("\n🎭 Emotions update new value:")
            for emo in data.get("emotions", []):
                print(f"  - {emo.get('type')}: {emo.get('level')}")

        else:
            print(f"⏳ Waiting choice authorization, received: {key}")

def find_activity(data: dict, client_key: str) -> dict | None:
    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            return wrapper[client_key]
    return None


async def send_json(ws, data: dict, label: str):
    payload = json.dumps(data)
    print(f"\n📤 Sending → {label}")
    await ws.send(payload)


async def wait_for_authorization(ws):
    while True:
        msg = await ws.recv()
        data = json.loads(msg)
        key = data.get("key")

        if key == "start_authorization":
            print("✅ start_authorization received. You may start.")
            return

        elif key == "update_emotions":
            print("\n🎭 Emotions update new value:")
            for emo in data.get("emotions", []):
                print(f"  - {emo.get('type')}: {emo.get('level')}")

        else:
            print("⏳ Waiting authorization, received:", key)
