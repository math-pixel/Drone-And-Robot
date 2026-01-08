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

    static let routes: [String: Route] = [
        "choice_activity_step_1_finished": ("throw_activity", "start_authorization"),
        "rover": ("presentation_activity", "start_authorization"),
        "presentation_activity_finished": ("test_activity", "start_authorization"),
        "test_activity_finished": ("choice_activity", "choice_activity_step_4_authorization"),
        "test_activity_start": ("test_activity", "test_activity_start"),
        "update_jauge_score": ("jauge_throw_activity", "update_jauge_score")
    ]

}


enum EmotionRouting {
    static let deltasByKey: [String: [String: Double]] = [
        "ouistiti": ["happiness": -10,  "stress": -10, "shame": -10, "angry": -10],
        
        "rover_forward_10_1": ["happiness": -0.1,  "stress": -10, "shame": -10, "angry": -10],
        
        "rover_forward_30_2": ["happiness": +10,  "stress": +10, "shame": +10, "angry": +10],
        "rover_forward_60_3": ["happiness": +3,  "stress": -2, "shame": -1, "angry": -2],
        "rover_left_90": ["happiness": -1,  "stress": +2, "shame": +5, "angry": +3],
        "test_activity_finished_step_1": ["happiness": +59,  "stress": +2, "shame": +5, "angry": +39],
        "presentation_sphero_activity_traveled": ["happiness": +0,  "stress": +40, "shame": +50, "angry": -12],
        
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
                ["type": "happiness", "level": 0.2],
                ["type": "stress",    "level": 0.7],
                ["type": "shame",     "level": 0],
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
