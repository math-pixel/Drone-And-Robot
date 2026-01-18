if __name__ == "__main__":
    import asyncio
    import json
    from WsClient_iot import WSClient
    from StepperMotor_esp import Stepper28BYJ48  

    STEPS = [
        {
            "id": 1,
            "actions": [
                {
                    "id": 1,
                    "type": "Activity_mom_stepper_motor",
                    "finished": False,
                }
            ],
            "authorized": False,
            "finished": False,
        },
    ]

    # ✅ Motor: création ici (pin à adapter)
    steperMoteur = Stepper28BYJ48(
        in1=17,
        in2=18,
        in3=27,
        in4=22,
        mode='half'
    )
    steperMoteur.init_position(0)
    
    
    time.sleep(2)
    print("go to 90 deg")
    steperMoteur.go_to(90)
    time.sleep(2)
    steperMoteur.go_to(0)


    def my_action_handler(action: dict, client: WSClient, step_id: int):
        pass
    
    def my_key_handler(data_dict: dict, client: WSClient):
        key = data_dict.get("key", "")
        print("📥 Key reçue = " + key)
        print("Data received: ", json.dumps(data_dict))
        
        prefix = "mom_activity_stepper_"
        command_prefix = "control_"
        
        # 1. Vérifie si c'est pour moi
        if not key.startswith(prefix):
            return # On quitte si ce n'est pas le bon préfixe

        # On récupère ce qui suit "mom_activity_stepper_"
        # Exemple: "90" ou "control_init_position"
        content = key[len(prefix):]

        # --- CAS 1 : C'est un chiffre (Angle direct) ---
        if content.isdigit():
            try:
                angle = int(content)
                angle = max(0, min(180, angle))
                print(f"🎯 Commande ANGLE: go_to({angle}°)")
                steperMoteur.go_to(angle)
            except ValueError:
                print(f"⚠️ Erreur conversion angle: {content}")

        # --- CAS 2 : C'est une commande (commence par control_) ---
        elif content.startswith(command_prefix):
            # On récupère ce qui suit "control_"
            # Exemple: "init_position" ou "turn_left_45"
            command_body = content[len(command_prefix):]
            print("🛠️ Command body = " + command_body)

            if command_body == "init_position":
                print("📍 Action: init_position(0°)")
                steperMoteur.init_position(0)

            elif command_body.startswith("turn_left_"):
                # On récupère juste le chiffre après "turn_left_"
                val_str = command_body.replace("turn_left_", "")
                try:
                    val = int(val_str)
                    print(f"🔄 Action: ROTATE Gauche (-{val}°)")
                    steperMoteur.rotate(-val)
                except ValueError:
                    print(f"⚠️ Valeur turn_left invalide: {val_str}")

            elif command_body.startswith("turn_right_"):
                # On récupère juste le chiffre après "turn_right_"
                val_str = command_body.replace("turn_right_", "")
                try:
                    val = int(val_str)
                    print(f"🔄 Action: ROTATE Droite (+{val}°)")
                    steperMoteur.rotate(val)
                except ValueError:
                    print(f"⚠️ Valeur turn_right invalide: {val_str}")


    
    if not connect_wifi():
        pass
    
    client = WSClient(
        url="ws://192.168.10.34:8057/ws",
        client_key="mom_stepper_activity",
        action_delegate=my_action_handler,
        key_delegate=my_key_handler,
        steps=STEPS,
    )

    try:
        asyncio.run(client.run())
    finally:
        steperMoteur.stop()
