if __name__ == "__main__":
    import asyncio
    from utils.WSClient import WSClient



    STEPS = [
        {
            "id": 1, 
            "actions": [
                {"id": 1, "type": "video", "file": "classe.mp4", "finished": False},
                {"id": 2, "type": "choice", "chosen": -1, "name": "question ?", "options": [
                    {"id": 1, "text": "Passer plus tard"},
                    {"id": 2, "text": "Aller direct au tableau"}
                ], "finished": False}
            ], 
            "authorized": False, 
            "finished": False
        },
    ]

    def _ask_4_numbers(
        prompt: str = "Enter 4 levels (happiness stress shame angry): "
    ) -> tuple[float, float, float, float]:
        while True:
            raw = input(prompt).strip().replace(",", ".")
            parts = raw.split()
            if len(parts) != 4:
                print("Please enter exactly 4 numbers, e.g. -26.5 -3 4 9.5")
                continue
            try:
                return tuple(float(x) for x in parts)  # type: ignore[return-value]
            except ValueError:
                print("Invalid input. Use numbers only, e.g. -26.5 -3 4 9.5")



    async def my_action_handler(action: dict, client: WSClient, step_id: int):
        x = 0
        while True:
            input("Press Enter to continue...")
            ### Emotion levels example
            d_h, d_s, d_sh, d_a = _ask_4_numbers()
            k = "update_emotions"
            client.set_emotion_levels(d_h, d_s, d_sh, d_a)
            # client.set_emotion_levels(12, 20, 3, 35)
            
            ### Jauge score example
            # k = "update_jauge_score"
            # client.set_score_throw(d_h)
            
            ### Rover control example
            # speed = input("Enter speed (0-100): ")
            # duration = input("Enter duration in seconds: ")
            # key = f"rover_forward_{speed}_{duration}"
            # await client._send_json(key=key)

            ### Stepper motor example
            # # k = "mom_activity_stepper_control_turn_right_90"
            # # k = "mom_activity_stepper_control_init_position"
            # x += 90
            # k = f'mom_activity_stepper_{x}'

            # k = "choice_activity_step_1_finished"
            # son = input("son")
            # k = f"global_sound_{son}"
            await client._send_json(key=k)
        

    client = WSClient(
            url="ws://192.168.10.123:8057/ws",
            client_key="atmosphere_activity",
            action_delegate=my_action_handler,
            steps=STEPS
        )
        
    asyncio.run(client.run())