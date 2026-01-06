//
//  ServerManagerWebSocket.swift
//  server-mood
//
//  Created by Thibaud Evrard on 17/12/2025.
//

import Foundation
import Swifter

extension ServerManager {

    // MARK: - Routes

    func addRoutes() {
        log("Adding WS route \(wsRoute)")

        server[wsRoute] = websocket(
            text: { [weak self] session, text in
                guard let self else { return }
                Task { @MainActor in self.onTextMessage(text, from: session) }
            },
            binary: { [weak self] session, binary in
                self?.log("WS binary (\(binary.count) bytes) -> echo")
                session.writeBinary(binary)
            },
            connected: { [weak self] session in
                guard let self else { return }
                Task { @MainActor in self.onClientConnected(session) }
            },
            disconnected: { [weak self] session in
                guard let self else { return }
                Task { @MainActor in self.onClientDisconnected(session) }
            }
        )

        log("WS route registered ✅")
    }

    // MARK: - Session events

    func onClientConnected(_ session: WebSocketSession) {
        let id = ObjectIdentifier(session)
        sessions.insert(id)
        sessionMap[id] = session

        log("🟢 WS client connected. clients=\(sessions.count)")

        // handshake only to this client
        var handshake = globalJSON
        handshake["key"] = "identification_request"
        if let wsAddr = wsServerAddress { handshake["ws_server_address"] = wsAddr }

        guard let text = stringify(json: handshake) else {
            log("❌ Failed to stringify handshake JSON")
            return
        }

        log("➡️ WS send HANDSHAKE ONLY to new client")
        session.writeText(text)
    }

    func onClientDisconnected(_ session: WebSocketSession) {
        let id = ObjectIdentifier(session)
        sessions.remove(id)
        sessionMap[id] = nil

        log("🔴 WS client disconnected. clients=\(sessions.count)")

        if let activity = sessionActivity[id] {
            sessionActivity[id] = nil
            sessionIdByActivity[activity] = ""

            sessionByActivity[activity] = nil
            refreshManualControlsAvailability()
            setSessionIdInGlobal(activityName: activity, sessionId: "")

            activityConnected[activity] = false
            setConnectedFalseInGlobal(activityName: activity)

            syncActivityFromGlobalJSON(activity)
            log("ℹ️ \(activity) disconnected -> connected=false (no broadcast)")
        }
    }

    func onTextMessage(_ text: String, from session: WebSocketSession) {
        log("⬅️ WS recv text (\(text.count) chars)")

        guard let data = text.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else {
            log("❌ Invalid JSON received")
            return
        }

        handleIncomingJSON(obj, from: session)
    }

    // MARK: - Switch-case on key

    func handleIncomingJSON(_ incoming: [String: Any], from session: WebSocketSession) {
        let key = (incoming["key"] as? String) ?? ""
        log("🔑 key=\(key.isEmpty ? "(empty)" : key)")

        switch key {

        case let k where k.hasPrefix("identification_"):
            let activityName = String(k.dropFirst("identification_".count))
            handleIdentification(activityName: activityName, incoming: incoming, from: session)
            
        case let k where k.trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("rover"):
            handleRoverWSCommand(key: k)
            
        case "update_emotions":
            if let incomingEmotions = incoming["emotions"] as? [[String: Any]] {
                globalJSON["emotions"] = incomingEmotions
                emotions = extractEmotionsFromGlobalJSON() // @Published -> UI updates
            }
            
            guard let session = getSessionForActivity("jauge_activity") else {
                log("🛑🛑🛑 ERROR: jauge_activity is NOT connected — cannot forward update_emotions 🛑🛑🛑")
                break
            }

            // forward EXACT incoming json, unchanged
            guard let text = stringify(json: incoming) else {
                log("❌ Failed to stringify incoming update_emotions payload")
                break
            }

            log("➡️ Forward update_emotions -> jauge_activity")
            session.writeText(text)

        case let k where k.contains("_activity_finished_step_"):
            if let (activityName, stepId) = parseFinishedStepKey(k) {
                handleFinishedStep(activityName: activityName, stepId: stepId, incoming: incoming, from: session)
            } else {
                log("❌ Invalid finished_step key format: \(k)")
            }
        
        case let k where k.hasPrefix("choice_activity_step_") && k.hasSuffix("_finished") && !k.contains("_finished_"):
            if let stepId = parseChoiceStepFinishedKey(k) {
                handleChoiceStepFinished(stepId: stepId, incoming: incoming, from: session)
            } else {
                log("❌ Invalid choice step finished key: \(k)")
            }
            
        case let k where k.hasPrefix("choice_activity_step_") && k.hasSuffix("_finished"):
            if let (stepId, actionId) = parseChoiceVideoFinishedKey(k) {
                handleChoiceVideoActionFinished(stepId: stepId, actionId: actionId, incoming: incoming, from: session)
            } else {
                log("❌ Invalid choice video finished key: \(k)")
            }
        
        case let k where k.hasPrefix("test_activity_step_1_action"):
            forwardIncomingJSON(
                incoming,
                toActivities: [
                    "answer_1_test_activity",
                    "answer_2_test_activity",
                    "answer_3_test_activity",
                    "test_activity",
                ],
                reason: k
            )

        case let k where k.hasPrefix("choice_activity_"):
            if let (stepId, actionId, selected) = parseChoiceSelectedKey(k) {
                handleChoiceSelected(stepId: stepId, actionId: actionId, selected: selected, incoming: incoming, from: session)
            } else {
                log("❌ Invalid choice selected key: \(k)")
            }
            
        case let k where k.hasPrefix("test_activity_step_1_action_") && k.hasSuffix("_started"):
            // Echo the exact same JSON to answer_1/2/3_test_activity
            for target in ["answer_1_test_activity", "answer_2_test_activity", "answer_3_test_activity"] {
                guard let targetSession = getSessionForActivity(target) else {
                    log("🛑🛑🛑 ERROR: \(target) is NOT connected — cannot forward \(k) 🛑🛑🛑")
                    continue
                }

                guard let text = stringify(json: incoming) else {
                    log("❌ Failed to stringify incoming JSON for forwarding \(k)")
                    continue
                }

                log("➡️ Forward \(k) -> \(target)")
                targetSession.writeText(text)
            }


        case let k where k.hasSuffix("_finished"):
            let activityName = String(k.dropLast("_finished".count))
            guard GlobalDataConfig.allowedActivities.contains(activityName) else {
                log("❌ finished for unknown activity: \(activityName)")
                break
            }
            // JSON already contains finished=true, just merge + refresh UI
            mergeIncomingActivityIntoGlobal(activityName: activityName, incoming: incoming)
            syncAllFromGlobalJSON()
            log("✅ \(activityName) finished=true (UI updated)")

        default:
            log("⚠️ Unhandled key: \(key)")
        }
        
        handleSequencingIfNeeded(incomingKey: key, incomingJSON: incoming)
        applyEmotionRoutingIfNeeded(incomingKey: key)

    }

    // MARK: - Case: identification

    func handleIdentification(activityName: String, incoming: [String: Any], from session: WebSocketSession) {
        
        guard GlobalDataConfig.allowedActivities.contains(activityName) else {
            log("❌ identification for unknown activity: \(activityName)")
            return
        }

        mergeIncomingActivityIntoGlobal(activityName: activityName, incoming: incoming)
        setConnectedTrueInGlobal(activityName: activityName)
        activityConnected[activityName] = true

        sessionActivity[ObjectIdentifier(session)] = activityName
        attachSession(activityName: activityName, session: session)

        syncActivityFromGlobalJSON(activityName)

        log("✅ Identified: \(activityName) -> connected=true (session stored)")
        sendGlobalJSON(to: session, reason: "identification ack \(activityName)")
    }
    
    func handleRoverWSCommand(key: String) {
        log("rover")
        NotificationCenter.default.post(
            name: .roverWSCommand,
            object: nil,
            userInfo: ["key": key]
        )
        log("🛰 rover -> \(key)")
    }

}

extension Notification.Name {
    static let roverWSCommand = Notification.Name("rover.ws.command")
}
