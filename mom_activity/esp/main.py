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
    print("go to 50 deg")
    steperMoteur.go_to(50)

    def my_action_handler(action: dict, client: WSClient, step_id: int):
        pass
    
    def my_key_handler(data: dict, client: WSClient):
        
        key = data.get("key", "")
        
        print("key = " + key)
        
        prefix = "mom_activity_stepper_"
        print(key.startswith(prefix))      
        # Vérifie si c'est pour moi
        if key.startswith(prefix):
            # Extraire la valeur après le préfixe
            angle_str = key[len(prefix):]
            
            try:
                angle = int(angle_str)
                angle = max(0, min(180, angle))
                
                print(f"🎯 Commande reçue: go_to({angle}°)")
                steperMoteur.go_to(angle)
            
            except ValueError:
                print(f"⚠️ Valeur invalide: {angle_str}")
    
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
