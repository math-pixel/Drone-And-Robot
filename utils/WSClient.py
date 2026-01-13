import asyncio
import json
import websockets
from typing import Callable, Awaitable, Protocol, List, Dict, Set, Optional, Union

# ======================================================
# TYPES
# ======================================================

class ActionDelegate(Protocol):
    """Protocol pour le delegate d'actions."""
    async def __call__(self, action: dict, client: "WSClient", step_id: int) -> None:
        ...

class KeyDelegate(Protocol):
    """Protocol pour le delegate de réception de messages."""
    async def __call__(self, data: dict, client: "WSClient") -> None:
        ...

# ======================================================
# WS CLIENT
# ======================================================

import asyncio
import json
import websockets
from typing import Optional, List, Dict, Set, Callable, Any

# Définition de types pour la clarté
ActionDelegate = Callable[[Dict, Any, int], Any]
KeyDelegate = Callable[[Dict, Any], Any]
ConnectionHandler = Callable[[bool, Any], Any]

class WSClient:
    """WebSocket client for activity management with Auto-Reconnection."""

    def __init__(
        self,
        url: str,
        client_key: str,
        action_delegate: ActionDelegate,
        key_delegate: Optional[KeyDelegate] = None,
        connection_handler: Optional[ConnectionHandler] = None, # ### MODIF : Nouveau paramètre
        steps: Optional[List[Dict]] = None
    ):
        self.url = url
        self.client_key = client_key
        self.action_delegate = action_delegate
        self.key_delegate = key_delegate
        self.connection_handler = connection_handler # ### MODIF : Stockage du handler
        self.steps = steps or []
        
        self.ws = None
        self.data = None
        self._finished_steps: Set[int] = set()
        self._running = False # ### MODIF : Pour contrôler la boucle de reconnexion

    # ======================================================
    # PUBLIC API
    # ======================================================

    async def run(self):
        """Point d'entrée principal avec reconnexion automatique."""
        self._running = True
        print(f"🚀 Starting client for {self.url}")

        while self._running:
            try:
                print(f"🔌 Connecting to {self.url}...")
                
                # ### MODIF : Gestion de la connexion et du cycle de vie
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    print("✅ WebSocket connected!")
                    self._notify_connection_status(True) # Notifier connexion
                    
                    try:
                        # 1. Attente identification_request
                        await self._wait_for_identification()
                        
                        # 2. Envoi identification avec steps
                        await self._send_identification()
                        
                        # 3. Boucle principale: gestion des steps
                        await self._main_loop()
                        
                    except websockets.ConnectionClosed:
                        print("⚠️ Connection lost inside main loop")
                        # L'exception remonte pour déclencher le finally du bloc async with
                    except Exception as e:
                        print(f"❌ Error during execution: {e}")
            
            except (OSError, ConnectionRefusedError, websockets.InvalidURI, websockets.InvalidHandshake) as e:
                print(f"❌ Connection attempt failed: {e}")
            
            # Une fois sorti du bloc 'async with', on est déconnecté
            self.ws = None
            if self._running:
                self._notify_connection_status(False) # Notifier déconnexion
                print("⏳ Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                print("🛑 Client stopped gracefully")

    def stop(self):
        """Arrête la boucle de reconnexion."""
        self._running = False
        # Si connecté, on pourrait fermer le socket, mais asyncio gère bien ça via la tâche
        print("🛑 Stop requested")

    async def send_action_finished(self, step_id: int, action_id: int):
        """Appelé par le delegate quand une action est terminée."""
        if self.data:
            self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_finished"
            await self._send_json()

    async def send_choice_result(self, step_id: int, action_id: int, choice: int):
        """Appelé par le delegate quand un choix est fait."""
        if self.data:
            self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_choice_{choice}"
            await self._send_json()

    # ======================================================
    # CONNECTION HANDLER
    # ======================================================
    
    # ### MODIF : Helper pour notifier l'état
    def _notify_connection_status(self, is_connected: bool):
        if self.connection_handler:
            try:
                # On peut utiliser asyncio.create_task si le handler est async, 
                # ou l'appeler direct s'il est synchrone. Ici on suppose synchrone ou rapide.
                if asyncio.iscoroutinefunction(self.connection_handler):
                    asyncio.create_task(self.connection_handler(is_connected, self))
                else:
                    self.connection_handler(is_connected, self)
            except Exception as e:
                print(f"⚠️ Connection handler error: {e}")

    # ======================================================
    # IDENTIFICATION
    # ======================================================

    async def _wait_for_identification(self):
        """Attend le message identification_request."""
        raw = await self.ws.recv()
        self.data = json.loads(raw)
        
        key = self.data.get("key")
        print(f"📥 Received: {key}")
        
        await self._notify_key_delegate(self.data)
        
        if key != "identification_request":
            raise RuntimeError(f"Expected 'identification_request', got '{key}'")

    async def _send_identification(self):
        """Envoie l'identification avec les steps."""
        self.data["key"] = f"identification_{self.client_key}"
        
        activity = self._find_activity()
        if activity:
            activity["connected"] = True
            activity["steps"] = self.steps
            print(f"✅ {self.client_key} identified with {len(self.steps)} steps")
        else:
            print(f"⚠️ Activity '{self.client_key}' not found in server data")
        
        await self._send_json()

    # ======================================================
    # MAIN LOOP
    # ======================================================

    async def _main_loop(self):
        """Boucle principale: écoute et traite les messages."""
        print("\n🎯 Waiting for step authorizations...")
        
        # Pas de try/except ici pour ConnectionClosed, on laisse remonter à run()
        while True:
            msg = await self.ws.recv()
            incoming = json.loads(msg)
            key = incoming.get("key", "")
            
            await self._notify_key_delegate(incoming)
            
            if self._is_step_authorization(key):
                step_id = self._extract_step_id(key)
                
                if step_id not in self._finished_steps:
                    print(f"\n🔓 Authorization received for step {step_id}")
                    self.data = incoming
                    await self._execute_step(step_id)
                    self._finished_steps.add(step_id)
                    
                    if self._all_steps_finished():
                        await self._send_activity_finished()
            else:
                self._handle_incoming(incoming)

    # ======================================================
    # KEY DELEGATE
    # ======================================================

    async def _notify_key_delegate(self, data: dict):
        if self.key_delegate is not None:
            try:
                # Supporte async ou sync delegate
                if asyncio.iscoroutinefunction(self.key_delegate):
                    await self.key_delegate(data, self)
                else:
                    self.key_delegate(data, self)
            except Exception as e:
                print(f"⚠️ Key delegate error: {e}")

    # ======================================================
    # STEP EXECUTION
    # ======================================================

    async def _execute_step(self, step_id: int):
        step = self._find_step(step_id)
        if not step:
            print(f"❌ Step {step_id} not found")
            return
        
        print(f"\n▶️ Executing step {step_id}...")
        step["authorized"] = True
        
        for action in step.get("actions", []):
            action_id = action.get("id")
            action_type = action.get("type")
            print(f"\n  🎬 Action {action_id} ({action_type})")
            
            # Supporte async ou sync delegate
            if asyncio.iscoroutinefunction(self.action_delegate):
                await self.action_delegate(action, self, step_id)
            else:
                self.action_delegate(action, self, step_id)
        
        step["finished"] = True
        await self._send_step_finished(step_id)

    async def _send_step_finished(self, step_id: int):
        self.data["key"] = f"{self.client_key}_step_{step_id}_finished"
        print(f"🏁 Step {step_id} finished")
        await self._send_json()

    async def _send_activity_finished(self):
        activity = self._find_activity()
        if activity:
            activity["finished"] = True
        self.data["key"] = f"{self.client_key}_finished"
        print(f"\n🎉 Activity '{self.client_key}' completed!")
        await self._send_json()

    # ======================================================
    # UTILITIES
    # ======================================================

    def _is_step_authorization(self, key: str) -> bool:
        return (key.startswith(f"{self.client_key}_step_") and key.endswith("_authorization"))

    def _extract_step_id(self, key: str) -> int:
        try:
            parts = key.split("_")
            step_index = parts.index("step") + 1
            return int(parts[step_index])
        except:
            return -1

    def _find_activity(self) -> Optional[Dict]:
        if not self.data: return None
        for wrapper in self.data.get("activity", []):
            if self.client_key in wrapper:
                return wrapper[self.client_key]
        return None

    def _find_step(self, step_id: int) -> Optional[Dict]:
        for step in self.steps:
            if step.get("id") == step_id:
                return step
        activity = self._find_activity()
        if activity:
            for step in activity.get("steps", []):
                if step.get("id") == step_id:
                    return step
        return None

    def _all_steps_finished(self) -> bool:
        return len(self._finished_steps) >= len(self.steps)

    def _handle_incoming(self, data: dict):
        key = data.get("key")
        if key == "update_emotions":
            print("\n🎭 Emotions update:")
            for emo in data.get("emotions", []):
                print(f"   - {emo.get('type')}: {emo.get('level')}")
        else:
            print(f"\n📥 Received: {key}")

    async def _send_json(self, key: Optional[str] = None):
        if not self.ws: return
        key = key or self.data.get("key", "unknown")
        self.data["key"] = key
        payload = json.dumps(self.data)
        print(f"📤 Sending → {key}")
        await self.ws.send(payload)

    async def send_data(self, data: dict):
        if self.ws:
            json_data = json.dumps(data) 
            await self.ws.send(json_data)

    def set_emotion_levels(self, happiness: float, stress: float, shame: float, angry: float) -> dict:
        if not self.data: return {}
        levels = {"happiness": float(happiness), "stress": float(stress), "shame": float(shame), "angry": float(angry)}
        emotions = self.data.get("emotions", [])
        for e in emotions:
            t = e.get("type")
            if t in levels:
                e["level"] = levels[t]
        return self.data
    
    def set_score_throw(self, score: float) -> dict:
        if self.data is None: return {}
        target_key = "throw_activity"
        for wrapper in self.data.get("activity", []):
            if target_key in wrapper and isinstance(wrapper[target_key], dict):
                wrapper[target_key]["score"] = float(score)
                break
        return self.data



# ======================================================
# EXEMPLE D'UTILISATION
# ======================================================

if __name__ == "__main__":
    
    # Définition des steps
    STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 5, "type": "video", "file": "classe.mp4", "finished": False},
                {"id": 6, "type": "choice", "name": "Au moment de devoir présenter l'exposé, que fais-je ?", 
                 "options": ["Passer plus tard", "Aller direct au tableau"], "chosen": -1}
            ], 
            "authorized": False, 
            "finished": False
        },
        {
            "id": 2, 
            "actions": [
                {"id": 1, "type": "video", "file": "remarque.mp4", "finished": False},
            ], 
            "authorized": False, 
            "finished": False
        },
        {
            "id": 3, 
            "actions": [
                {"id": 1, "type": "video", "file": "recreation.mp4", "finished": False},
            ], 
            "authorized": False, 
            "finished": False
        },
    ]

    # ======================================================
    # KEY DELEGATE (appelé à chaque message reçu)
    # ======================================================
    
    # async def my_key_handler(data: dict, client: WSClient):
    #     """
    #     Delegate appelé à chaque réception de message.
    #     Permet de réagir à n'importe quel message du serveur.
    #     """
    #     key = data.get("key", "")
        
    #     print(f"🔑 [KEY DELEGATE] Received: {key}")
        
    #     # Exemples de traitement personnalisé
    #     match key:
    #         case "update_emotions":
    #             emotions = data.get("emotions", [])
    #             print(f"   → Emotions received: {len(emotions)} items")
    #             # Faire quelque chose avec les émotions...
                
    #         case "pause_requested":
    #             print("   → ⏸️ Server requested pause!")
    #             # Mettre en pause le client...
                
    #         case "custom_event":
    #             payload = data.get("payload", {})
    #             print(f"   → Custom event with payload: {payload}")
    #             # Traiter l'événement personnalisé...
                
    #         case _ if key.endswith("_authorization"):
    #             print(f"   → Step authorization detected")
                
    #         case _:
    #             pass  # Ignorer les autres clés

    # ======================================================
    # ACTION DELEGATE (gestion des actions)
    # ======================================================
    
    # async def my_action_handler(action: dict, client: WSClient, step_id: int):
    #     """Delegate personnalisé pour gérer les actions."""
    #     action_id = action.get("id")
    #     action_type = action.get("type")
        
    #     match action_type:
    #         case "video":
    #             file = action.get("file")
    #             print(f"     🎥 Playing video: {file}")
    #             input(f"     ⏸️  Press Enter when video '{file}' is finished...")
    #             action["finished"] = True
    #             await client.send_action_finished(step_id, action_id)
                
    #         case "choice":
    #             name = action.get("name")
    #             options = action.get("options", [])
                
    #             print(f"     ❓ {name}")
    #             for i, opt in enumerate(options):
    #                 print(f"        [{i}] {opt}")
                
    #             selected = -1
    #             while selected not in range(len(options)):
    #                 try:
    #                     selected = int(input("     👉 Your choice: "))
    #                 except ValueError:
    #                     print("     ⚠️  Invalid input")
                
    #             action["chosen"] = selected
    #             await client.send_choice_result(step_id, action_id, selected)
                
    #         case _:
    #             print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================
    
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,  # ← Nouveau paramètre
        steps=STEPS
    )
    
    asyncio.run(client.run())