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
        ],
        "presentation_activity_finished": [
            ("choice_activity", "choice_activity_step_3_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
        ],
        "choice_activity_step_3_finished": [
            ("test_activity", "test_activity_step_1_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
        ],
        "test_activity_finished": [
          ("choice_activity", "choice_activity_step_4_authorization"),
          ("sound_atmosphere_activity", "global_sound_sonnerie"),
        ],
        "choice_activity_step_4_finished": [
            ("throw_activity", "throw_activity_step_1_authorization"),
            ("sound_atmosphere_activity", "global_sound_sonnerie"),
        ],
        "throw_activity_finished": [
          ("choice_activity", "choice_activity_step_5_authorization"),
          ("sound_atmosphere_activity", "global_sound_sonnerie"),
        ],
        "choice_activity_step_5_finished": [
            ("choice_activity", "choice_activity_step_6_authorization"),
        ],


        "test_activity_start": [
            ("test_activity", "test_activity_start"),
        ],
        
    ]
}



enum EmotionRouting {
    static let deltasByKey: [String: [String: Double]] = [
        "choice_activity_step_1_action_3_choice_0": ["happiness": 5,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_1_action_3_choice_1": ["happiness": 10,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_1_action_7_choice_0": ["happiness": 7,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_1_action_7_choice_1": ["happiness": 0,  "stress": 3, "shame": 0, "angry": 0],
        "choice_activity_step_1_action_11_choice_0": ["happiness": 0,  "stress": 10, "shame": 0, "angry": 0],
        "choice_activity_step_1_action_11_choice_1": ["happiness": 10,  "stress": -18, "shame": 0, "angry": 0],
        "choice_activity_step_3_action_3_choice_0": ["happiness": 18,  "stress": 0, "shame": 10, "angry": 0],
        "choice_activity_step_3_action_3_choice_1": ["happiness": -10,  "stress": 0, "shame": 10, "angry": 0],
        "choice_activity_step_4_action_3_choice_0": ["happiness": 0,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_4_action_3_choice_1": ["happiness": 0,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_5_action_3_choice_0": ["happiness": 0,  "stress": 0, "shame": 0, "angry": 0],
        "choice_activity_step_5_action_3_choice_1": ["happiness": 0,  "stress": 0, "shame": 0, "angry": 0],
        
        
        "choice_activity_step_1_action_9_finished": ["happiness": 0,  "stress": 18, "shame": 0, "angry": 0],
        
        "crie_4": ["happiness": 0,  "stress": -1, "shame": -1, "angry": -1],
        "crie_5": ["happiness": 0,  "stress": -2, "shame": -2, "angry": -2],
        
        
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
        "sound_atmosphere_activity"
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
