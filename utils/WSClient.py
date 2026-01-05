import asyncio
import json
import websockets
from typing import Callable, Awaitable, Protocol


# ======================================================
# TYPES
# ======================================================

class ActionDelegate(Protocol):
    """Protocol pour le delegate d'actions."""
    async def __call__(self, action: dict, client: "WSClient") -> None:
        ...


# ======================================================
# WS CLIENT
# ======================================================

class WSClient:
    """WebSocket client for activity management."""

    def __init__(
        self,
        url: str,
        client_key: str,
        action_delegate: ActionDelegate,
        steps: list[dict] | None = None
    ):
        self.url = url
        self.client_key = client_key
        self.action_delegate = action_delegate
        self.steps = steps or []
        
        self.ws = None
        self.data = None
        self._finished_steps: set[int] = set()

    # ======================================================
    # PUBLIC API
    # ======================================================

    async def run(self):
        """Point d'entrée principal."""
        print(f"🔌 Connecting to {self.url}...")

        async with websockets.connect(self.url) as ws:
            self.ws = ws
            
            # 1. Attente identification_request
            await self._wait_for_identification()
            
            # 2. Envoi identification avec steps
            await self._send_identification()
            
            # 3. Boucle principale: gestion des steps
            await self._main_loop()

    async def send_action_finished(self, step_id: int, action_id: int):
        """Appelé par le delegate quand une action est terminée."""
        self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_finished"
        await self._send_json()

    async def send_choice_result(self, step_id: int, action_id: int, choice: int):
        """Appelé par le delegate quand un choix est fait."""
        self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_choice_{choice}"
        await self._send_json()

    # ======================================================
    # IDENTIFICATION
    # ======================================================

    async def _wait_for_identification(self):
        """Attend le message identification_request."""
        raw = await self.ws.recv()
        self.data = json.loads(raw)
        
        key = self.data.get("key")
        print(f"📥 Received: {key}")
        
        if key != "identification_request":
            raise RuntimeError(f"Expected 'identification_request', got '{key}'")

    async def _send_identification(self):
        """Envoie l'identification avec les steps."""
        # Mise à jour des données
        self.data["key"] = f"identification_{self.client_key}"
        
        # Trouver et configurer l'activité
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
        
        try:
            while True:
                msg = await self.ws.recv()
                incoming = json.loads(msg)
                key = incoming.get("key", "")
                
                # Vérifier si c'est une autorisation de step
                if self._is_step_authorization(key):
                    step_id = self._extract_step_id(key)
                    
                    if step_id not in self._finished_steps:
                        print(f"\n🔓 Authorization received for step {step_id}")
                        self.data = incoming  # ⚠️ Mise à jour data avec le nouveau message
                        await self._execute_step(step_id)
                        self._finished_steps.add(step_id)
                        
                        # Vérifier si tous les steps sont terminés
                        if self._all_steps_finished():
                            await self._send_activity_finished()
                else:
                    # Autres messages (emotions, etc.)
                    self._handle_incoming(incoming)
                    
        except websockets.ConnectionClosed:
            print("\n🔌 Connection closed")
        except KeyboardInterrupt:
            print("\n🛑 Client stopped by user")

    # ======================================================
    # STEP EXECUTION
    # ======================================================

    async def _execute_step(self, step_id: int):
        """Exécute toutes les actions d'un step via le delegate."""
        step = self._find_step(step_id)
        
        if not step:
            print(f"❌ Step {step_id} not found")
            return
        
        print(f"\n▶️ Executing step {step_id}...")
        
        # Marquer le step comme autorisé
        step["authorized"] = True
        
        # Exécuter chaque action via le delegate
        for action in step.get("actions", []):
            action_id = action.get("id")
            action_type = action.get("type")
            
            print(f"\n  🎬 Action {action_id} ({action_type})")
            
            # Appel du delegate (l'utilisateur gère le match case)
            await self.action_delegate(action, self, step_id)
        
        # Marquer le step comme terminé
        step["finished"] = True
        await self._send_step_finished(step_id)

    async def _send_step_finished(self, step_id: int):
        """Envoie la notification de fin de step."""
        self.data["key"] = f"{self.client_key}_step_{step_id}_finished"
        print(f"🏁 Step {step_id} finished")
        await self._send_json()

    async def _send_activity_finished(self):
        """Envoie la notification de fin d'activité."""
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
        """Vérifie si la clé est une autorisation de step."""
        return (
            key.startswith(f"{self.client_key}_step_") 
            and key.endswith("_authorization")
        )

    def _extract_step_id(self, key: str) -> int:
        """Extrait l'ID du step depuis la clé d'autorisation."""
        # Format: "{client_key}_step_{id}_authorization"
        parts = key.split("_")
        step_index = parts.index("step") + 1
        return int(parts[step_index])

    def _find_activity(self) -> dict | None:
        """Trouve l'activité dans les données."""
        for wrapper in self.data.get("activity", []):
            if self.client_key in wrapper:
                return wrapper[self.client_key]
        return None

    def _find_step(self, step_id: int) -> dict | None:
        """Trouve un step par son ID."""
        # Chercher dans les steps locaux
        for step in self.steps:
            if step.get("id") == step_id:
                return step
        
        # Chercher dans les données serveur
        activity = self._find_activity()
        if activity:
            for step in activity.get("steps", []):
                if step.get("id") == step_id:
                    return step
        
        return None

    def _all_steps_finished(self) -> bool:
        """Vérifie si tous les steps sont terminés."""
        return len(self._finished_steps) >= len(self.steps)

    def _handle_incoming(self, data: dict):
        """Gère les messages entrants non-authorization."""
        key = data.get("key")
        
        if key == "update_emotions":
            print("\n🎭 Emotions update:")
            for emo in data.get("emotions", []):
                print(f"   - {emo.get('type')}: {emo.get('level')}")
        else:
            print(f"\n📥 Received: {key}")

    async def _send_json(self):
        """Envoie les données JSON actuelles."""
        payload = json.dumps(self.data)
        key = self.data.get("key", "unknown")
        print(f"📤 Sending → {key}")
        await self.ws.send(payload)


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
    # DELEGATE (à personnaliser par l'utilisateur)
    # ======================================================
    
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        """
        Delegate personnalisé pour gérer les actions.
        L'utilisateur implémente ici son match case.
        """
        action_id = action.get("id")
        action_type = action.get("type")
        
        match action_type:
            case "video":
                file = action.get("file")
                print(f"     🎥 Playing video: {file}")
                
                # Simulation: attendre que la vidéo soit "jouée"
                input(f"     ⏸️  Press Enter when video '{file}' is finished...")
                
                # Marquer comme terminé
                action["finished"] = True
                await client.send_action_finished(step_id, action_id)
                
            case "choice":
                name = action.get("name")
                options = action.get("options", [])
                
                print(f"     ❓ {name}")
                for i, opt in enumerate(options):
                    print(f"        [{i}] {opt}")
                
                # Attendre le choix
                selected = -1
                while selected not in range(len(options)):
                    try:
                        selected = int(input("     👉 Your choice: "))
                    except ValueError:
                        print("     ⚠️  Invalid input")
                
                # Enregistrer le choix
                action["chosen"] = selected
                await client.send_choice_result(step_id, action_id, selected)
                
            case _:
                print(f"     ⚠️  Unknown action type: {action_type}")

    # ======================================================
    # RUN
    # ======================================================
    
    client = WSClient(
        url="ws://192.168.10.182:8057/ws",
        client_key="choice_activity",
        action_delegate=my_action_handler,
        steps=STEPS
    )
    
    asyncio.run(client.run())