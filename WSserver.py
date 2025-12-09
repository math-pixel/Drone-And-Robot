import asyncio
import websockets
import json
import os

class AdvancedWSServer:
    def __init__(self, config_file="config.json"):
        self.config = self._load_config(config_file)
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8765)
        print(f"[*] Configuration chargée: {self.host}:{self.port}")

    def _load_config(self, path):
        """Charge la configuration depuis un fichier JSON."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Le fichier de config {path} est introuvable.")
        
        with open(path, 'r') as f:
            return json.load(f)

    async def start(self):
        """Démarre le serveur WebSocket."""
        print(f"[*] Démarrage du serveur sur ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            # Maintient le serveur en vie indéfiniment
            await asyncio.Future()

    async def handler(self, websocket):
        """Gère chaque connexion entrante."""
        client_address = websocket.remote_address
        print(f"[+] Nouveau client connecté : {client_address}")

        try:
            async for message in websocket:
                # 1. Afficher le message brut reçu
                print(f"\n[REÇU] Message brut : {message}")

                # Tentative de parsing JSON
                try:
                    data = json.loads(message)
                    
                    # 2. Vérification de la condition spécifique
                    if isinstance(data, dict) and data.get("name") == "global_data_transfer":
                        print(">>> JSON CIBLE DÉTECTÉ <<<")
                        print(json.dumps(data, indent=4, ensure_ascii=False))
                        
                        # 3. Appel de la méthode process
                        await self.process(data, websocket)
                
                except json.JSONDecodeError:
                    # Ce n'est pas du JSON, on ignore la suite logique
                    pass

        except websockets.ConnectionClosed:
            print(f"[-] Connexion fermée : {client_address}")

    async def process(self, data, websocket):
        """
        Méthode appelée uniquement si le JSON est valide et correspond au critère.
        Ici, tu mets ta logique métier.
        """
        print("[*] Traitement des données en cours...")
        
        # Exemple d'actions basées sur le contenu du JSON
        payload = data.get("payload", {})
        
        # Action 1 : Sauvegarder dans un fichier (exemple)
        # with open("data_log.txt", "a") as f:
        #     f.write(str(payload) + "\n")
        
        # Action 2 : Répondre au client actuel
        response = {"status": "success", "message": "Données global_data_transfer traitées"}
        await websocket.send(json.dumps(response))
        
        # Action 3 : Déclencher un appel vers un autre serveur (Client mode)
        # Par exemple, si on veut relayer l'info
        if "forward_to_remote" in payload and payload["forward_to_remote"]:
             target = self.config.get("remote_server_uri", "ws://localhost:9000")
             await self.call_external_ws(target, data)

    async def call_external_ws(self, uri, data_to_send):
        """
        Méthode pour agir en tant que client et appeler un autre serveur WS.
        """
        print(f"[*] Tentative de connexion au serveur distant : {uri}")
        try:
            async with websockets.connect(uri) as remote_ws:
                message = json.dumps(data_to_send)
                await remote_ws.send(message)
                print(f"[*] Données envoyées au serveur distant.")
                
                # Attendre une réponse éventuelle du serveur distant
                response = await remote_ws.recv()
                print(f"[*] Réponse du serveur distant : {response}")
                return response
        except Exception as e:
            print(f"[!] Erreur lors de l'appel au serveur distant : {e}")

if __name__ == "__main__":
    server = AdvancedWSServer("config.json")
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n[*] Arrêt du serveur.")
