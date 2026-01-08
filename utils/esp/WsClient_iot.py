# ws_client.py - WSClient pour MicroPython ESP32 avec uwebsockets

import uwebsockets.client
import ujson
import time
import _thread


class WSClient:
    """WebSocket client pour ESP32 MicroPython"""

    def __init__(self, url, client_key, action_delegate=None, key_delegate=None, steps=None):
        self.url = url
        self.client_key = client_key
        self.action_delegate = action_delegate
        self.key_delegate = key_delegate
        self.steps = steps or []
        
        self.ws = None
        self.data = None
        self.connected = False
        self._finished_steps = set()
        self._lock = False
        self._running = False

    # ======================================================
    # PUBLIC API
    # ======================================================

    def run(self):
        """Point d'entrée principal (bloquant)"""
        print(f"🔌 Connecting to {self.url}...")
        self._running = True
        self._connect()

    def run_background(self):
        """Lance la connexion en arrière-plan (non-bloquant)"""
        self._running = True
        _thread.start_new_thread(self._maintain_connection, ())

    def stop(self):
        """Arrête le client"""
        self._running = False
        self.connected = False
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

    def send_action_finished(self, step_id, action_id):
        """Appelé quand une action est terminée"""
        if self.data:
            self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_finished"
            self._send_json()

    def send_choice_result(self, step_id, action_id, choice):
        """Appelé quand un choix est fait"""
        if self.data:
            self.data["key"] = f"{self.client_key}_step_{step_id}_action_{action_id}_choice_{choice}"
            self._send_json()

    def send_data(self, data):
        """Envoie des données arbitraires"""
        if self.ws and self.connected:
            try:
                self.ws.send(ujson.dumps(data))
                print(f"📤 Sent: {data.get('key', 'data')}")
            except Exception as e:
                print(f"⚠️ Send error: {e}")
                self.connected = False

    # ======================================================
    # CONNECTION MANAGEMENT
    # ======================================================

    def _maintain_connection(self):
        """Thread de maintien de connexion"""
        while self._running:
            if not self.connected and not self._lock:
                self._lock = True
                self._connect()
                self._lock = False
            time.sleep(2)

    def _connect(self):
        """Établit la connexion et lance la boucle principale"""
        try:
            print(f"🔌 Connecting to {self.url}...")
            self.ws = uwebsockets.client.connect(self.url)
            print("✅ WebSocket connected!")
            self.connected = True
            
            # Boucle de réception
            self._main_loop()
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.connected = False
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
                self.ws = None

    # ======================================================
    # MAIN LOOP
    # ======================================================

    def _main_loop(self):
        """Boucle principale de réception"""
        identification_done = False
        
        while self.connected and self._running:
            try:
                msg = self.ws.recv()
                
                if not msg:
                    time.sleep(0.05)
                    continue
                
                print(f"📥 Received message")
                
                try:
                    incoming = ujson.loads(msg)
                except:
                    print("⚠️ Invalid JSON")
                    continue
                
                key = incoming.get("key", "")
                
                # Notifier le key delegate
                self._notify_key_delegate(incoming)
                
                # Phase 1: Identification
                if not identification_done:
                    if key == "identification_request":
                        print("📥 Identification request received")
                        self.data = incoming
                        self._send_identification()
                        identification_done = True
                        print("\n🎯 Waiting for step authorizations...")
                    continue
                
                # Phase 2: Gestion des steps et messages
                if self._is_step_authorization(key):
                    step_id = self._extract_step_id(key)
                    
                    if step_id not in self._finished_steps:
                        print(f"\n🔓 Authorization for step {step_id}")
                        self.data = incoming
                        self._execute_step(step_id)
                        self._finished_steps.add(step_id)
                        
                        if self._all_steps_finished():
                            self._send_activity_finished()
                else:
                    self._handle_incoming(incoming)
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"❌ Receive error: {e}")
                self.connected = False
                break
        
        print("🔌 Connection closed")

    # ======================================================
    # KEY DELEGATE
    # ======================================================

    def _notify_key_delegate(self, data):
        """Notifie le key_delegate si défini"""
        if self.key_delegate is not None:
            try:
                self.key_delegate(data, self)
            except Exception as e:
                print(f"⚠️ Key delegate error: {e}")

    # ======================================================
    # IDENTIFICATION
    # ======================================================

    def _send_identification(self):
        """Envoie l'identification avec les steps"""
        self.data["key"] = f"identification_{self.client_key}"
        
        activity = self._find_activity()
        if activity:
            activity["connected"] = True
            activity["steps"] = self.steps
            print(f"✅ {self.client_key} identified with {len(self.steps)} steps")
        else:
            print(f"⚠️ Activity '{self.client_key}' not found")
        
        self._send_json()

    # ======================================================
    # STEP EXECUTION
    # ======================================================

    def _execute_step(self, step_id):
        """Exécute toutes les actions d'un step"""
        step = self._find_step(step_id)
        
        if not step:
            print(f"❌ Step {step_id} not found")
            return
        
        print(f"\n▶️ Executing step {step_id}...")
        step["authorized"] = True
        
        for action in step.get("actions", []):
            action_id = action.get("id")
            action_type = action.get("type")
            print(f"  🎬 Action {action_id} ({action_type})")
            
            # Appel du delegate
            if self.action_delegate:
                try:
                    self.action_delegate(action, self, step_id)
                except Exception as e:
                    print(f"⚠️ Action delegate error: {e}")
        
        step["finished"] = True
        self._send_step_finished(step_id)

    def _send_step_finished(self, step_id):
        """Envoie la notification de fin de step"""
        self.data["key"] = f"{self.client_key}_step_{step_id}_finished"
        print(f"🏁 Step {step_id} finished")
        self._send_json()

    def _send_activity_finished(self):
        """Envoie la notification de fin d'activité"""
        activity = self._find_activity()
        if activity:
            activity["finished"] = True
        
        self.data["key"] = f"{self.client_key}_finished"
        print(f"\n🎉 Activity '{self.client_key}' completed!")
        self._send_json()

    # ======================================================
    # UTILITIES
    # ======================================================

    def _is_step_authorization(self, key):
        """Vérifie si la clé est une autorisation de step"""
        return (
            key.startswith(f"{self.client_key}_step_") 
            and key.endswith("_authorization")
        )

    def _extract_step_id(self, key):
        """Extrait l'ID du step depuis la clé"""
        parts = key.split("_")
        step_index = parts.index("step") + 1
        return int(parts[step_index])

    def _find_activity(self):
        """Trouve l'activité dans les données"""
        if not self.data:
            return None
        for wrapper in self.data.get("activity", []):
            if self.client_key in wrapper:
                return wrapper[self.client_key]
        return None

    def _find_step(self, step_id):
        """Trouve un step par son ID"""
        for step in self.steps:
            if step.get("id") == step_id:
                return step
        
        activity = self._find_activity()
        if activity:
            for step in activity.get("steps", []):
                if step.get("id") == step_id:
                    return step
        return None

    def _all_steps_finished(self):
        """Vérifie si tous les steps sont terminés"""
        return len(self._finished_steps) >= len(self.steps)

    def _handle_incoming(self, data):
        """Gère les messages entrants non-authorization"""
        key = data.get("key", "")
        
        if key == "update_emotions":
            print("\n🎭 Emotions update:")
            for emo in data.get("emotions", []):
                print(f"   - {emo.get('type')}: {emo.get('level')}")
        else:
            print(f"📥 Key: {key}")

    def _send_json(self):
        """Envoie les données JSON actuelles"""
        if self.ws and self.connected and self.data:
            try:
                payload = ujson.dumps(self.data)
                key = self.data.get("key", "unknown")
                self.ws.send(payload)
                print(f"📤 Sent → {key}")
            except Exception as e:
                print(f"⚠️ Send error: {e}")
                self.connected = False