import asyncio
import websockets
import json
import time

PORT = 8080

async def handler(websocket):
    client_addr = websocket.remote_address
    print(f"\n[+] Nouveau client connecté : {client_addr}")
    
    try:
        # 1. PROTOCOLE : Le client attend "identification_request" dès le début
        # On ajoute des champs vides pour éviter les KeyError dans ton client
        init_message = {
            "key": "identification_request",
            "activity": [], 
            "emotions": []
        }
        await websocket.send(json.dumps(init_message))
        print(" -> Envoi de 'identification_request'")

        # 2. Boucle d'écoute
        async for message in websocket:
            try:
                data = json.loads(message)
                key = data.get("key", "Inconnue")
                print(f" <- Reçu : {key}")
                
                # Si le client s'identifie, on peut lui répondre (optionnel pour ce test)
                if key.startswith("identification_"):
                    print("    (Client identifié avec succès)")

            except json.JSONDecodeError:
                print(" <- Reçu : Message non-JSON")

    except websockets.ConnectionClosedError:
        print(f"[-] Connexion fermée brutalement : {client_addr}")
    except websockets.ConnectionClosedOK:
        print(f"[-] Déconnexion propre : {client_addr}")
    except Exception as e:
        print(f"[!] Erreur : {e}")
    finally:
        print(f"--- Fin de session pour {client_addr} ---")

async def main():
    print(f"🚀 Serveur WebSocket démarré sur ws://0.0.0.0:{PORT}")
    print("Appuyez sur CTRL+C pour arrêter le serveur et tester la reconnexion des clients.")
    
    # Écoute sur toutes les interfaces (0.0.0.0)
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # Garde le serveur en vie indéfiniment

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Serveur arrêté manuellement.")