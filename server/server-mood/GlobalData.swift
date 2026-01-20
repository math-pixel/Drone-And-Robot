//
//  GlobalData.swift
//  server-mood
//
//  Created by Thibaud Evrard on 17/12/2025.
//

import Foundation

struct ActivityStep: Identifiable, Hashable {
    let id: String
    let name: String
    let finished: Bool
}

struct ChoiceStep: Identifiable, Hashable {
    let id: String
    let authorized: Bool
    let finished: Bool
    let actions: [ChoiceAction]
}

struct ChoiceAction: Identifiable, Hashable {
    let id: String
    let type: String              // "video" | "choice"
    let file: String?             // video
    let finished: Bool?           // video
    let name: String?             // choice
    let options: [String]         // choice
    let chosen: Int               // choice (-1/0/1)
}

struct ActivityAction: Identifiable, Hashable {
    let id: String
    let type: String              // "video" | "choice" | ...
    let file: String?             // video
    let finished: Bool?           // video
    let name: String?             // choice
    let options: [String]?        // choice
    let chosen: Int?              // choice (-1/0/1)
}

struct ActivityActionStep: Identifiable, Hashable {
    let id: String
    let authorized: Bool
    let finished: Bool
    let actions: [ActivityAction]
}

struct EmotionItem: Identifiable, Hashable {
    let id = UUID()
    let type: String
    let level: Double
}

enum Sequencing {

    typealias Route = (targetActivity: String, outgoingKey: String)

    // ✅ now a key can trigger multiple routes
    static let routes: [String: [Route]] = [
        "choice_activity_step_1_finished": [
            ("choice_activity", "choice_activity_step_2_authorization"),
        ],
        "choice_activity_step_2_finished": [
            ("presentation_activity", "presentation_activity_step_1_authorization"),
            ("presentation_sphero_activity", "presentation_sphero_activity_step_1_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
            ("sound_atmosphere_activity", "global_sound_loop_chuchottement"),
            ("light_atmosphere_activity", "update_light_4_on"),
            ("light_atmosphere_activity", "update_light_2_off"),
        ],
        "presentation_activity_finished": [
            ("sound_atmosphere_activity", "global_sound_end_loop_chuchottement"),
            ("choice_activity", "choice_activity_step_3_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
            ("sound_atmosphere_activity", "global_sound_presentation_end"),
            ("light_atmosphere_activity", "update_light_4_off"),
            ("light_atmosphere_activity", "update_light_2_on"),
            ("presentation_sphero_activity", "presentation_activity_finished"),
        ],
        "choice_activity_step_3_finished": [
            ("test_activity", "test_activity_step_1_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
            ("sound_atmosphere_activity", "global_sound_test_intro"),
            ("light_atmosphere_activity", "update_light_3_on"),
            ("light_atmosphere_activity", "update_light_2_off"),
        ],
        "test_activity_finished": [
          ("choice_activity", "choice_activity_step_4_authorization"),
          ("sound_atmosphere_activity", "global_sound_sonnerie"),
          ("sound_atmosphere_activity", "global_sound_test_intro"),
          ("light_atmosphere_activity", "update_light_3_off"),
          ("light_atmosphere_activity", "update_light_2_on"),
        ],
        "test_activity_step_1_finished": [
          ("choice_activity", "choice_activity_step_4_authorization"),
          ("sound_atmosphere_activity", "global_sound_sonnerie"),
          ("light_atmosphere_activity", "update_light_3_off"),
          ("light_atmosphere_activity", "update_light_2_on"),
        ],
        "choice_activity_step_4_finished": [
            ("throw_activity", "throw_activity_step_1_authorization"),
            ("sound_atmosphere_activity", "global_sound_throw_intro"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
            ("light_atmosphere_activity", "update_light_1_on"),
            ("light_atmosphere_activity", "update_light_2_off"),
        ],
        "throw_activity_finished": [
          ("choice_activity", "choice_activity_step_5_authorization"),
          ("sound_atmosphere_activity", "global_sound_sonnerie"),
          ("light_atmosphere_activity", "update_light_1_off"),
          ("light_atmosphere_activity", "update_light_2_on"),
        ],
        "choice_activity_step_5_finished": [
            ("choice_activity", "choice_activity_step_6_authorization"),
        ],


        "test_activity_start": [
            ("test_activity", "test_activity_start"),
        ],
        
        "mom_activity_stepper_control_turn_right_10": [
          ("sound_atmosphere_activity", "global_sound_positif_1"),
          ("sound_atmosphere_activity", "global_sound_rire"),
        ],
        
        "update_emotions":
            [
                ("sound_atmosphere_activity", "global_sound_update_emotions"),
            ]
    ]
}



enum EmotionRouting {
    static let deltasByKey: [String: [String: Double]] = [
        "choice_activity_step_1_action_1_finished": ["happiness": 37,  "stress": 37, "shame": 37, "angry": 37],
        "choice_activity_step_1_action_2_finished": ["happiness": -25,  "stress": -30, "shame":-36, "angry": -36],
        
        "choice_activity_step_2_action_3_choice_0": ["happiness": 5,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_2_action_3_choice_1": ["happiness": 10,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_2_action_7_choice_0": ["happiness": 7,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_2_action_7_choice_1": ["happiness": 0,  "stress": -1, "shame": 0, "angry": 0],
        "choice_activity_step_2_action_11_choice_0": ["happiness": 0,  "stress": 10, "shame": 0, "angry": 0],
        "choice_activity_step_2_action_11_choice_1": ["happiness": 10,  "stress": -18, "shame": 0, "angry": 0],
        
        "choice_activity_step_3_action_2_finished": ["happiness": 5,  "stress": -1, "shame": 0, "angry": 0],
        "choice_activity_step_3_action_3_finished": ["happiness": 0,  "stress": 10, "shame": 0, "angry": 0],
        
        
        "choice_activity_step_4_action_5_choice_0": ["happiness": 18,  "stress": 0, "shame": 15, "angry": 0],
        "choice_activity_step_4_action_5_choice_1": ["happiness": -10,  "stress": 0, "shame": 15, "angry": 0],
        "cine_4_5_choice_1": ["happiness": 18,  "stress": 0, "shame": 15, "angry": 0],

        "choice_activity_step_5_action_1_finished": ["happiness": 0,  "stress": 20, "shame": 10, "angry": 30],
        
        "choice_activity_step_6_action_4_choice_0": ["happiness": +20,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_6_action_4_choice_1": ["happiness": +20,  "stress": 0, "shame": 0, "angry": 0],
        
        "throw_activity_finished": ["happiness": -37,  "stress": +37, "shame": +37, "angry": +37],
        
        "choice_activity_step_6_action_7_choice_0": ["happiness": +16,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_6_action_7_choice_1": ["happiness": +16,  "stress": 0, "shame": 0, "angry": 0],
        
        "good_answer": ["happiness": 1,  "stress": 0, "shame": 0, "angry": 0],
        "wrong_answer": ["happiness": -5,  "stress": 0, "shame": 3, "angry": 1],
        "no_answer": ["happiness": 0,  "stress": 1, "shame": 1, "angry": 3],
        
        "bad_word": ["happiness": -1,  "stress": 5, "shame": 2, "angry": 2],
        
        "test_activity_step_1_finished": ["happiness": -22,  "stress": 0, "shame": 5, "angry": 0],
        "test_activity_finished": ["happiness": -22,  "stress": 0, "shame": 5, "angry": 0],
        
        "mom_activity_stepper_control_turn_right_10": ["happiness": 2,  "stress": 0, "shame": 0, "angry": 0],
        "global_sound_prof_nrv": ["happiness": -5,  "stress": 0, "shame": 5, "angry": 1],
        "global_sound_prof_heho": ["happiness": -7,  "stress": 0, "shame": 5, "angry": 1],
        "global_sound_prof_fin": ["happiness": -12,  "stress": 0, "shame": 15, "angry": 3],

        "crie_4": ["happiness": 0,  "stress": -1, "shame": -1, "angry": -1],
        "crie_5": ["happiness": 0,  "stress": -1, "shame": -1, "angry": -1],
        
        
    ]
}

enum GlobalDataConfig {

    static let allowedActivities: Set<String> = [
        "atmosphere_activity",
        "test_activity",
        "presentation_activity",
        "presentation_sphero_activity",
        "throw_activity",
        "mom_activity",
        "choice_activity",
        "main_activity",
        "throw_rover_actitvity",
        "jauge_throw_activity",
        "answer_1_test_activity",
        "answer_2_test_activity",
        "answer_3_test_activity",
        "jauge_activity",
        "mom_stepper_activity",
        "sound_atmosphere_activity",
        "light_atmosphere_activity"
    ]

    static func makeInitialGlobalJSON(wsServerAddress: String) -> [String: Any] {
        [
            "name": "global_data_transfer",
            "version": "1.0.0",
            "ws_server_address": wsServerAddress,
            "key": "identification_request",
            "started": false,
            "message": "",
            "emotions": [
                ["type": "happiness", "level": 12],
                ["type": "stress",    "level": 7],
                ["type": "shame",     "level": 1],
                ["type": "angry",     "level": 1],
            ],
            "activity": [
                [
                    "atmosphere_activity": [
                        "ws_session_id": "",
                        "connected": false,
                        "dmx": [
                            ["lamp1": ["channel": 1, "value": 255]],
                            ["lamp2": ["channel": 2, "value": 128]],
                        ],
                        "sound": [
                            "file": "background_music.mp3",
                            "volume": 0.8,
                            "loop": true
                        ]
                    ]
                ],
                [
                    "sound_atmosphere_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "light_atmosphere_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "test_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "answer_1_test_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "answer_2_test_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "answer_3_test_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "presentation_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "mom_stepper_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "jauge_throw_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "presentation_sphero_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "throw_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "steps": [],
                        "score": 0
                    ]
                ],
                [
                    "mom_activity": [
                        "authorized": false,
                        "finished": false,
                        "ws_session_id": "",
                        "connected": false,
                        "step": [],
                        "llm_model": "gpt-4",
                        "llm_server_address": "http://"
                    ]
                ],
                [
                    "throw_rover_actitvity": [
                        "authorized": false,
                        "finished": false,
                        "connected": false,
                        "steps": [],
                    ]
                ],
                [
                    "choice_activity": [
                        "ws_session_id": "",
                        "connected": false,
                        "steps": []
                    ]
                ],
                [
                    "jauge_activity": [
                        "ws_session_id": "",
                        "connected": false
                    ]
                ]
            ]
        ]
    }
}
