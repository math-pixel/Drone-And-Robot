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

        // answers a/b/c up to 20
        "test_activity_step_1_action_1_a": ("test_activity", "test_activity_step_1_action_1_a"),
        "test_activity_step_1_action_1_b": ("test_activity", "test_activity_step_1_action_1_b"),
        "test_activity_step_1_action_1_c": ("test_activity", "test_activity_step_1_action_1_c"),
        "test_activity_step_1_action_2_a": ("test_activity", "test_activity_step_1_action_2_a"),
        "test_activity_step_1_action_2_b": ("test_activity", "test_activity_step_1_action_2_b"),
        "test_activity_step_1_action_2_c": ("test_activity", "test_activity_step_1_action_2_c"),
        "test_activity_step_1_action_3_a": ("test_activity", "test_activity_step_1_action_3_a"),
        "test_activity_step_1_action_3_b": ("test_activity", "test_activity_step_1_action_3_b"),
        "test_activity_step_1_action_3_c": ("test_activity", "test_activity_step_1_action_3_c"),
        "test_activity_step_1_action_4_a": ("test_activity", "test_activity_step_1_action_4_a"),
        "test_activity_step_1_action_4_b": ("test_activity", "test_activity_step_1_action_4_b"),
        "test_activity_step_1_action_4_c": ("test_activity", "test_activity_step_1_action_4_c"),
        "test_activity_step_1_action_5_a": ("test_activity", "test_activity_step_1_action_5_a"),
        "test_activity_step_1_action_5_b": ("test_activity", "test_activity_step_1_action_5_b"),
        "test_activity_step_1_action_5_c": ("test_activity", "test_activity_step_1_action_5_c"),
        "test_activity_step_1_action_6_a": ("test_activity", "test_activity_step_1_action_6_a"),
        "test_activity_step_1_action_6_b": ("test_activity", "test_activity_step_1_action_6_b"),
        "test_activity_step_1_action_6_c": ("test_activity", "test_activity_step_1_action_6_c"),
        "test_activity_step_1_action_7_a": ("test_activity", "test_activity_step_1_action_7_a"),
        "test_activity_step_1_action_7_b": ("test_activity", "test_activity_step_1_action_7_b"),
        "test_activity_step_1_action_7_c": ("test_activity", "test_activity_step_1_action_7_c"),
        "test_activity_step_1_action_8_a": ("test_activity", "test_activity_step_1_action_8_a"),
        "test_activity_step_1_action_8_b": ("test_activity", "test_activity_step_1_action_8_b"),
        "test_activity_step_1_action_8_c": ("test_activity", "test_activity_step_1_action_8_c"),
        "test_activity_step_1_action_9_a": ("test_activity", "test_activity_step_1_action_9_a"),
        "test_activity_step_1_action_9_b": ("test_activity", "test_activity_step_1_action_9_b"),
        "test_activity_step_1_action_9_c": ("test_activity", "test_activity_step_1_action_9_c"),
        "test_activity_step_1_action_10_a": ("test_activity", "test_activity_step_1_action_10_a"),
        "test_activity_step_1_action_10_b": ("test_activity", "test_activity_step_1_action_10_b"),
        "test_activity_step_1_action_10_c": ("test_activity", "test_activity_step_1_action_10_c"),
        "test_activity_step_1_action_11_a": ("test_activity", "test_activity_step_1_action_11_a"),
        "test_activity_step_1_action_11_b": ("test_activity", "test_activity_step_1_action_11_b"),
        "test_activity_step_1_action_11_c": ("test_activity", "test_activity_step_1_action_11_c"),
        "test_activity_step_1_action_12_a": ("test_activity", "test_activity_step_1_action_12_a"),
        "test_activity_step_1_action_12_b": ("test_activity", "test_activity_step_1_action_12_b"),
        "test_activity_step_1_action_12_c": ("test_activity", "test_activity_step_1_action_12_c"),
        "test_activity_step_1_action_13_a": ("test_activity", "test_activity_step_1_action_13_a"),
        "test_activity_step_1_action_13_b": ("test_activity", "test_activity_step_1_action_13_b"),
        "test_activity_step_1_action_13_c": ("test_activity", "test_activity_step_1_action_13_c"),
        "test_activity_step_1_action_14_a": ("test_activity", "test_activity_step_1_action_14_a"),
        "test_activity_step_1_action_14_b": ("test_activity", "test_activity_step_1_action_14_b"),
        "test_activity_step_1_action_14_c": ("test_activity", "test_activity_step_1_action_14_c"),
        "test_activity_step_1_action_15_a": ("test_activity", "test_activity_step_1_action_15_a"),
        "test_activity_step_1_action_15_b": ("test_activity", "test_activity_step_1_action_15_b"),
        "test_activity_step_1_action_15_c": ("test_activity", "test_activity_step_1_action_15_c"),
        "test_activity_step_1_action_16_a": ("test_activity", "test_activity_step_1_action_16_a"),
        "test_activity_step_1_action_16_b": ("test_activity", "test_activity_step_1_action_16_b"),
        "test_activity_step_1_action_16_c": ("test_activity", "test_activity_step_1_action_16_c"),
        "test_activity_step_1_action_17_a": ("test_activity", "test_activity_step_1_action_17_a"),
        "test_activity_step_1_action_17_b": ("test_activity", "test_activity_step_1_action_17_b"),
        "test_activity_step_1_action_17_c": ("test_activity", "test_activity_step_1_action_17_c"),
        "test_activity_step_1_action_18_a": ("test_activity", "test_activity_step_1_action_18_a"),
        "test_activity_step_1_action_18_b": ("test_activity", "test_activity_step_1_action_18_b"),
        "test_activity_step_1_action_18_c": ("test_activity", "test_activity_step_1_action_18_c"),
        "test_activity_step_1_action_19_a": ("test_activity", "test_activity_step_1_action_19_a"),
        "test_activity_step_1_action_19_b": ("test_activity", "test_activity_step_1_action_19_b"),
        "test_activity_step_1_action_19_c": ("test_activity", "test_activity_step_1_action_19_c"),
        "test_activity_step_1_action_20_a": ("test_activity", "test_activity_step_1_action_20_a"),
        "test_activity_step_1_action_20_b": ("test_activity", "test_activity_step_1_action_20_b"),
        "test_activity_step_1_action_20_c": ("test_activity", "test_activity_step_1_action_20_c"),
    ]

}


enum EmotionRouting {
    static let deltasByKey: [String: [String: Double]] = [
        "choice_activity_1_2_0": ["happiness": +8,  "stress": -4, "shame": -2, "angry": -1],
        "choice_activity_1_2_1": ["happiness": -2,  "stress": +6, "shame": +3, "angry": +2],
        "choice_activity_2_2_0": ["happiness": +3,  "stress": -2, "shame": -1, "angry": -2],
        "choice_activity_2_2_1": ["happiness": -1,  "stress": +2, "shame": +5, "angry": +3],
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
        "answer_1_test_activity",
        "answer_2_test_activity",
        "answer_3_test_activity",
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
                ["type": "happiness", "level": 7.0],
                ["type": "stress",    "level": 4],
                ["type": "shame",     "level": 3],
                ["type": "angry",     "level": 2],
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
                        "number_of_points_detected": 0
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
            ]
        ]
    }
}
