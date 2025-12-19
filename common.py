import asyncio
import json
import websockets


class WSClient:
    """WebSocket client for activity management."""
    
    def __init__(self, url: str = "ws://192.168.10.182:8057/ws"):
        self.url = url
        self.ws = None
        self.data = None
        self.client_key = None
        self.items = None

    # ======================================================
    # MAIN
    # ======================================================

    async def run(self, client_key: str, items: list[dict] | None = None):
        self.client_key = client_key
        self.items = items
        
        input(f"Press Enter to connect to {self.url}...")

        async with websockets.connect(self.url) as ws:
            self.ws = ws
            raw = await self.ws.recv()
            self.data = json.loads(raw)

            print("\n📥 Initial key:", self.data.get("key"))

            if self.data.get("key") == "identification_request":
                self.data, mode = self._handle_identification()
                await self._send_json(f"identification_{self.client_key}")

                if mode == "step":
                    if self.client_key == "choice_activity":
                        await self._handle_choice_steps()
                    else:
                        print("⏳ Waiting for start_authorization...")
                        await self._wait_for_authorization()
                        await self._handle_steps()

            print("\n✅ Client ready. Waiting for server (Ctrl+C to exit)\n")
            try:
                while True:
                    msg = await self.ws.recv()
                    self._handle_incoming(json.loads(msg))
            except KeyboardInterrupt:
                print("\n🛑 Client stopped by user")

    # ======================================================
    # IDENTIFICATION
    # ======================================================

    def _handle_identification(self) -> tuple[dict, str | None]:
        self.data["key"] = f"identification_{self.client_key}"

        for wrapper in self.data.get("activity", []):
            if self.client_key in wrapper:
                activity = wrapper[self.client_key]
                activity["connected"] = True
                activity["step"] = self.items
                print(f"✅ {self.client_key} activated (step)")
                return self.data, "step"

        print(f"⚠️ Activity '{self.client_key}' not found")
        return self.data, None

    # ======================================================
    # STANDARD STEPS (non choice_activity)
    # ======================================================

    async def _handle_steps(self):
        activity = self._find_activity()
        steps = activity.get("step", [])

        for index, step in enumerate(steps, start=1):
            input(f"\n➡️ Press Enter to finish step {index}: {step.get('name')}")

            step["finished"] = True
            self.data["key"] = f"{self.client_key}_finished_step_{index}"
            await self._send_json(self.data["key"])

        activity["finished"] = True
        self.data["key"] = f"{self.client_key}_finished"
        await self._send_json(self.data["key"])

    # ======================================================
    # CHOICE ACTIVITY
    # ======================================================

    async def _handle_choice_steps(self):
        activity = self._find_activity()
        steps = {step["id"]: step for step in activity.get("step", [])}
        finished_steps = set()

        print("\n🎯 Waiting for step authorizations (any order)...")

        while len(finished_steps) < len(steps):
            msg = await self.ws.recv()
            incoming = json.loads(msg)
            key = incoming.get("key")

            if key == "update_emotions":
                self._handle_incoming(incoming)
                continue

            if key and key.startswith(f"{self.client_key}_step_") and key.endswith("_authorization"):
                step_id = int(key.split("_")[3])

                if step_id in finished_steps:
                    continue

                print(f"\n✅ Authorization received for step {step_id}")

                self.data = incoming
                await self._execute_choice_step(step_id)

                finished_steps.add(step_id)

        print("\n🏁 choice_activity completed")

    async def _execute_choice_step(self, step_id: int):
        activity = self._find_activity()
        step = next(s for s in activity["step"] if s["id"] == step_id)

        for action in step.get("actions", []):
            action_id = action["id"]

            if action["type"] == "video":
                input(f"\n🎬 Press Enter to finish video {action['file']}")
                action["finished"] = True
                self.data["key"] = f"{self.client_key}_step_{step_id}_{action_id}_finished"
                await self._send_json(self.data["key"])

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
                self.data["key"] = f"{self.client_key}_{step_id}_{action_id}_{selected}"
                await self._send_json(self.data["key"])

        step["finished"] = True
        self.data["key"] = f"{self.client_key}_step_{step_id}_finished"

        print(f"🏁 Step {step_id} finished")
        await self._send_json(self.data["key"])

    # ======================================================
    # AUTHORIZATION
    # ======================================================

    async def _wait_for_step_authorization(self, step_id: int) -> dict:
        expected_key = f"choice_activity_step_{step_id}_authorization"

        while True:
            msg = await self.ws.recv()
            data = json.loads(msg)
            key = data.get("key")

            if key == expected_key:
                print(f"✅ Authorization received for step {step_id}")
                return data

            elif key == "update_emotions":
                print("\n🎭 Emotions update new value:")
                for emo in data.get("emotions", []):
                    print(f"  - {emo.get('type')}: {emo.get('level')}")

            else:
                print(f"⏳ Waiting step {step_id} authorization, received: {key}")

    async def _wait_for_authorization(self):
        while True:
            msg = await self.ws.recv()
            data = json.loads(msg)

            if data.get("key") == "start_authorization":
                return
            else:
                self._handle_incoming(data)

    # ======================================================
    # UTILITIES
    # ======================================================

    def _handle_incoming(self, data: dict):
        key = data.get("key")

        if key == "update_emotions":
            print("\n🎭 Emotions update:")
            for emo in data.get("emotions", []):
                print(f"  - {emo['type']}: {emo['level']}")
        else:
            print("\n📥 Received:", key)

    def _find_activity(self) -> dict | None:
        for wrapper in self.data.get("activity", []):
            if self.client_key in wrapper:
                return wrapper[self.client_key]
        return None

    async def _send_json(self, label: str):
        payload = json.dumps(self.data)
        print(f"\n📤 Sending → {label}")
        await self.ws.send(payload)


# ======================================================
# USAGE
# ======================================================

if __name__ == "__main__":
    client = WSClient()
    asyncio.run(client.run("choice_activity", items=[
        {"id": 1, "name": "Step 1"},
        {"id": 2, "name": "Step 2"},
    ]))