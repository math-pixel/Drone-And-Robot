import asyncio
import json
import websockets

WS_URL = "ws://192.168.10.182:8057/ws"

# ======================================================
# MAIN
# ======================================================

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
                if client_key == "choice_activity":
                    # 🚫 PAS de start_authorization ici
                    await handle_choice_steps(ws, data, client_key)
                else:
                    # ✅ start_authorization seulement pour les autres
                    print("⏳ Waiting for start_authorization...")
                    await wait_for_authorization(ws)
                    await handle_steps(ws, data, client_key)

        print("\n✅ Client ready. Waiting for server (Ctrl+C to exit)\n")
        try:
            while True:
                msg = await ws.recv()
                handle_incoming(json.loads(msg))
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")


# ======================================================
# IDENTIFICATION
# ======================================================

def handle_identification(data: dict, client_key: str, items: list[dict]):
    data["key"] = f"identification_{client_key}"

    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            activity = wrapper[client_key]
            activity["connected"] = True
            activity["step"] = items
            print(f"✅ {client_key} activated (step)")
            return data, "step"

    print(f"⚠️ Activity '{client_key}' not found")
    return data, None

# ======================================================
# STANDARD STEPS (non choice_activity)
# ======================================================

async def handle_steps(ws, data: dict, client_key: str):
    activity = find_activity(data, client_key)
    steps = activity.get("step", [])

    for index, step in enumerate(steps, start=1):
        input(f"\n➡️ Press Enter to finish step {index}: {step.get('name')}")

        step["finished"] = True
        data["key"] = f"{client_key}_finished_step_{index}"
        await send_json(ws, data, data["key"])

    activity["finished"] = True
    data["key"] = f"{client_key}_finished"
    await send_json(ws, data, data["key"])

# ======================================================
# CHOICE ACTIVITY (NEW LOGIC)
# ======================================================
async def handle_choice_steps(ws, data: dict, client_key: str):
    activity = find_activity(data, client_key)
    steps = {step["id"]: step for step in activity.get("step", [])}
    finished_steps = set()

    print("\n🎯 Waiting for step authorizations (any order)...")

    while len(finished_steps) < len(steps):
        msg = await ws.recv()
        incoming = json.loads(msg)
        key = incoming.get("key")

        # 🎭 émotions toujours traitées
        if key == "update_emotions":
            handle_incoming(incoming)
            continue

        # 🔑 Autorisation de step
        if key and key.startswith(f"{client_key}_step_") and key.endswith("_authorization"):
            step_id = int(key.split("_")[3])

            if step_id in finished_steps:
                continue  # déjà fait

            print(f"\n✅ Authorization received for step {step_id}")

            data = incoming  # 🔴 TRÈS IMPORTANT
            await execute_choice_step(ws, data, client_key, step_id)

            finished_steps.add(step_id)

    print("\n🏁 choice_activity completed")

async def execute_choice_step(ws, data: dict, client_key: str, step_id: int):
    activity = find_activity(data, client_key)
    step = next(s for s in activity["step"] if s["id"] == step_id)

    for action in step.get("actions", []):
        action_id = action["id"]

        if action["type"] == "video":
            input(f"\n🎬 Press Enter to finish video {action['file']}")
            action["finished"] = True
            data["key"] = f"{client_key}_step_{step_id}_{action_id}_finished"
            await send_json(ws, data, data["key"])

        elif action["type"] == "choice":
            print(f"\n🔘 Choice: {action['name']}")
            for i, opt in enumerate(action["options"]):
                print(f"  {i}: {opt}")

            selected = None
            while selected not in (0, 1):
                try:
                    selected = int(input("➡️ Choose 0 or 1: "))
                except ValueError:
                    pass

            action["chosen"] = selected
            data["key"] = f"{client_key}_{step_id}_{action_id}_{selected}"
            await send_json(ws, data, data["key"])

    # ✅ STEP TERMINÉ
    step["finished"] = True
    data["key"] = f"{client_key}_step_{step_id}_finished"

    print(f"🏁 Step {step_id} finished")
    await send_json(ws, data, data["key"])



# ======================================================
# AUTHORIZATION
# ======================================================

async def wait_for_step_authorization(ws, step_id: int) -> dict:
    expected_key = f"choice_activity_step_{step_id}_authorization"

    while True:
        msg = await ws.recv()
        data = json.loads(msg)
        key = data.get("key")

        if key == expected_key:
            print(f"✅ Authorization received for step {step_id}")
            return data  # ⬅️ IMPORTANT

        elif key == "update_emotions":
            print("\n🎭 Emotions update new value:")
            for emo in data.get("emotions", []):
                print(f"  - {emo.get('type')}: {emo.get('level')}")

        else:
            print(f"⏳ Waiting step {step_id} authorization, received: {key}")


async def wait_for_authorization(ws):
    while True:
        msg = await ws.recv()
        data = json.loads(msg)

        if data.get("key") == "start_authorization":
            return
        else:
            handle_incoming(data)

# ======================================================
# UTILITIES
# ======================================================

def handle_incoming(data: dict):
    key = data.get("key")

    if key == "update_emotions":
        print("\n🎭 Emotions update:")
        for emo in data.get("emotions", []):
            print(f"  - {emo['type']}: {emo['level']}")
    else:
        print("\n📥 Received:", key)

def find_activity(data: dict, client_key: str) -> dict | None:
    for wrapper in data.get("activity", []):
        if client_key in wrapper:
            return wrapper[client_key]
    return None

async def send_json(ws, data: dict, label: str):
    payload = json.dumps(data)
    print(f"\n📤 Sending → {label}")
    await ws.send(payload)
