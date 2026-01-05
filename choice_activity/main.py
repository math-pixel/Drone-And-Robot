import sys
import os
import threading
import asyncio

# --- BLOC MAGIQUE A METTRE TOUT EN HAUT ---
current_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_path)
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from WSClient import WSClient
from utils.rpi.Bouton import *

# ======================================================
# CONFIGURATION DES BOUTONS
# ======================================================

# Variable globale pour stocker quel bouton a été appuyé
idButtonPressed = None

# Création des boutons (Attention: changer les pins selon ton câblage réel)
# btnLeft sur GPIO 17, btnRight sur GPIO 27 (exemple)
btnLeft = Bouton(pin=17, pull_up=True, long_press_time=2.0)
btnRight = Bouton(pin=27, pull_up=True, long_press_time=2.0) 

# Fonction de callback qui modifie la variable globale
def signal_button_press(btn_id):
    global idButtonPressed
    print(f"👉 Hardware: Bouton {btn_id} appuyé")
    idButtonPressed = btn_id

# On utilise lambda pour passer l'ID ('left' ou 'right') quand le bouton est pressé
btnLeft.on_press = lambda: signal_button_press("left")
btnRight.on_press = lambda: signal_button_press("right")

# Callbacks optionnels pour le feedback
def on_release_feedback(duration):
    print(f"   (Relâché après {duration:.2f}s)")

btnLeft.on_release = on_release_feedback
btnRight.on_release = on_release_feedback


if __name__ == "__main__":
    
    # Définition des steps
    STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 1, "type": "video", "file": "classe.mp4", "finished": False},
                {"id": 2, "type": "choice", "options": [
                    {"id": 1, "text": "Passer plus tard (Bouton Gauche)"},
                    {"id": 2, "text": "Aller direct au tableau (Bouton Droite)"}
                ], "finished": False}
            ], 
            "authorized": False, 
            "finished": False
        },
    ]

    # ======================================================
    # DELEGATE
    # ======================================================
    
    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        # On déclare utiliser la variable globale définie plus haut
        global idButtonPressed 
        
        action_id = action.get("id")
        action_type = action.get("type")
        
        match action_type:
            case "video":
                file = action.get("file")
                print(f"     🎥 Playing video: {file}")
                
                # Simulation: attendre que la vidéo soit "jouée"
                # input(f"     ⏸️  Press Enter when video '{file}' is finished...")
                await asyncio.sleep(2) # Simulation auto pour l'exemple
                
                # Marquer comme terminé
                action["finished"] = True
                await client.send_action_finished(step_id, action_id)
                
            case "choice":
                name = action.get("name")
                options = action.get("options", [])
                
                print(f"\n     ❓ CHOIX : {name}")
                print(f"     👉 Appuyez sur GAUCHE pour '{options[0]['text']}'")
                print(f"     👉 Appuyez sur DROITE pour '{options[1]['text']}'")
                
                # --- INTÉGRATION BOUTONS ICI ---
                
                # 1. On réinitialise l'état avant d'attendre
                idButtonPressed = None
                
                # 2. Boucle d'attente non bloquante
                # On boucle tant que idButtonPressed est None (personne n'a appuyé)
                while idButtonPressed is None:
                    # await asyncio.sleep est CRUCIAL ici. 
                    # Il rend la main au processeur pour gérer le WebSocket et les callbacks GPIO
                    await asyncio.sleep(0.1)
                
                # 3. Identification du choix basé sur le bouton
                selected = -1
                
                if idButtonPressed == "left":
                    selected = 0 # Premier élément de la liste options
                    print("     ✅ Sélection : GAUCHE")
                elif idButtonPressed == "right":
                    if len(options) > 1:
                        selected = 1 # Deuxième élément
                        print("     ✅ Sélection : DROITE")
                    else:
                        selected = 0 # Fallback si une seule option
                
                # --- FIN INTÉGRATION ---

                # Enregistrer le choix
                if selected != -1:
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
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
        btnLeft.cleanup()
        btnRight.cleanup()