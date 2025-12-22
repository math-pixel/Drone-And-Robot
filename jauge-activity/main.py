if __name__ == "__main__":
    
    # --- IMPORTS ---
    from utils.rpi.BandeauLED import BandeauLED # Adapte le chemin selon où tu as mis le fichier

    # --- CONFIGURATION LED ---
    # Initialisation du bandeau (GPIO 18 est le standard pour les LEDs)
    LEDS_TOTAL = 30  # Nombre total de LEDs sur ton ruban
    led_strip = BandeauLED(num_leds=LEDS_TOTAL, pin=18, luminosite=100)

    def afficher_jauge(pourcentage, couleur="vert"):
        """
        Allume un pourcentage du bandeau (0 à 100)
        """
        # Sécurité : on borne entre 0 et 100
        pourcentage = max(0, min(100, pourcentage))
        
        # --- LE PRODUIT EN CROIX ---
        # (Pourcentage * NombreTotal) / 100
        nb_leds_allumees = int((pourcentage * led_strip.num_leds) / 100)
        
        # On parcourt toutes les LEDs du bandeau
        for i in range(led_strip.num_leds):
            if i < nb_leds_allumees:
                # Allumer
                led_strip.set_pixel(i, couleur, auto_afficher=False)
            else:
                # Éteindre le reste
                led_strip.set_pixel(i, "noir", auto_afficher=False)
                
        # On envoie l'info au bandeau une seule fois à la fin
        led_strip.afficher()

    # Définition des steps
    STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 1, "type": "video", "file": "classe.mp4", "finished": False},
                {"id": 2, "type": "choice", "options": [
                    {"id": 1, "text": "Passer plus tard"},
                    {"id": 2, "text": "Aller direct au tableau"}
                ], "finished": False}
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
            case "update_emotion":
                # transformer les strip led
                await client.send_choice_result(step_id, action_id, selected)
                
                # Enregistrer le choix
                action["chosen"] = selected
            case "gauge":
                # Récupération de la valeur (0 à 100)
                valeur = action.get("value", 0)
                
                # Optionnel : récupérer une couleur si envoyée, sinon bleu par défaut
                couleur = action.get("color", "bleu")
                
                print(f"     📊 Mise à jour jauge : {valeur}% ({couleur})")
                
                # Appel de la fonction
                afficher_jauge(valeur, couleur)
                
                # On signale que c'est fait
                action["finished"] = True
                await client.send_action_finished(step_id, action_id)
                
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