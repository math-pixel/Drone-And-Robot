import Foundation
import Swifter
import Darwin

extension ServerManager {

    // MARK: - Send

    func sendGlobalJSON(to session: WebSocketSession, reason: String) {
        guard let text = stringify(json: globalJSON) else {
            log("❌ Failed to stringify global JSON")
            return
        }
        log("➡️ WS send global JSON (\(text.count) chars) reason=\(reason)")
        session.writeText(text)
    }

    // MARK: - Global JSON mutations

    func mergeIncomingActivityIntoGlobal(activityName: String, incoming: [String: Any]) {
        guard let incomingActivities = incoming["activity"] as? [[String: Any]] else {
            log("⚠️ incoming has no 'activity' array -> nothing to merge")
            return
        }

        guard let container = incomingActivities.first(where: { $0[activityName] != nil }),
              let activityPayload = container[activityName] as? [String: Any]
        else {
            log("⚠️ incoming activity payload not found for \(activityName)")
            return
        }

        guard var globalActivities = globalJSON["activity"] as? [[String: Any]] else { return }

        if let idx = globalActivities.firstIndex(where: { $0[activityName] != nil }) {
            globalActivities[idx] = [activityName: activityPayload]
        } else {
            globalActivities.append([activityName: activityPayload])
        }

        globalJSON["activity"] = globalActivities
        log("Merged incoming payload into global JSON for \(activityName)")
        syncActivityFromGlobalJSON(activityName)
    }

    func setConnectedTrueInGlobal(activityName: String) {
        guard var globalActivities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = globalActivities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = globalActivities[idx][activityName] as? [String: Any] else { return }
        payload["connected"] = true
        globalActivities[idx][activityName] = payload
        globalJSON["activity"] = globalActivities
    }

    func setConnectedFalseInGlobal(activityName: String) {
        guard var globalActivities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = globalActivities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = globalActivities[idx][activityName] as? [String: Any] else { return }
        payload["connected"] = false
        globalActivities[idx][activityName] = payload
        globalJSON["activity"] = globalActivities
    }

    func setAllConnectedFalseInGlobal() {
        guard var globalActivities = globalJSON["activity"] as? [[String: Any]] else { return }
        for (i, obj) in globalActivities.enumerated() {
            guard let name = obj.keys.first,
                  var payload = obj[name] as? [String: Any]
            else { continue }

            if GlobalDataConfig.allowedActivities.contains(name) {
                payload["connected"] = false
                payload["ws_session_id"] = ""
                globalActivities[i] = [name: payload]
            }
        }
        globalJSON["activity"] = globalActivities
    }
    
    func applyEmotionRoutingIfNeeded(incomingKey: String) {
        guard let deltas = EmotionRouting.deltasByKey[incomingKey] else { return }

        applyEmotionDeltas(deltas)          // updates globalJSON + UI + sends update_emotions to atmosphere
        log("✅ EmotionRouting applied for key=\(incomingKey)")
    }

    // MARK: - Sync UI from globalJSON

    func syncAllFromGlobalJSON() {
        if activityOrder.isEmpty {
            activityOrder = extractActivityOrderFromGlobalJSON()
        }

        for name in activityOrder {
            syncActivityFromGlobalJSON(name)
            activityAuthorized[name] = extractAuthorized(activityName: name)
            sessionIdByActivity[name] = extractSessionId(activityName: name) ?? ""
            activityConnected[name] = extractConnected(activityName: name) ?? false
            activityFinished[name] = extractFinished(activityName: name)
        }

        emotions = extractEmotionsFromGlobalJSON()
        canStartActivity = (getSessionForActivity("choice_activity") != nil)
        activityStarted = extractStarted()
        canStartActivity = (getSessionForActivity("choice_activity") != nil) && !activityStarted
    }

    func extractActivityOrderFromGlobalJSON() -> [String] {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return [] }
        return activities.compactMap { $0.keys.first }
    }

    func extractSessionId(activityName: String) -> String? {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return nil }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any]
        else { return nil }
        return payload["ws_session_id"] as? String
    }

    func extractConnected(activityName: String) -> Bool? {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return nil }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any]
        else { return nil }
        return payload["connected"] as? Bool
    }

    func syncActivityFromGlobalJSON(_ activityName: String) {
        activityActionSteps[activityName] = extractActionSteps(activityName: activityName)
        activitySteps[activityName] = [] // garde compat
        debugDumpActivity(activityName)
    }
    
    func debugDumpActivity(_ name: String) {
        guard let activities = globalJSON["activity"] as? [[String: Any]],
              let obj = activities.first(where: { $0[name] != nil }),
              let payload = obj[name] as? [String: Any]
        else {
            log("🧪 DEBUG \(name): not found in globalJSON.activity")
            return
        }
    }

    
    private func extractActionSteps(activityName: String) -> [ActivityActionStep] {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return [] }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any],
              let rawStepsAny = payload["steps"] as? [Any]
        else { return [] }

        let steps = rawStepsAny.compactMap { $0 as? [String: Any] }
        guard steps.contains(where: { $0["actions"] != nil }) else { return [] }

        func idString(_ any: Any?) -> String {
            if let i = any as? Int { return String(i) }
            if let s = any as? String { return s }
            return String(describing: any ?? "")
        }

        return steps.compactMap { s in
            guard let rawActionsAny = s["actions"] as? [Any] else { return nil }
            let actionsRaw = rawActionsAny.compactMap { $0 as? [String: Any] }

            let stepId = idString(s["id"])
            let authorized = (s["authorized"] as? Bool) ?? false
            let finished = (s["finished"] as? Bool) ?? false

            let actions: [ActivityAction] = actionsRaw.map { a in
                let actionId = idString(a["id"])
                let type = (a["type"] as? String) ?? ""

                let file = a["file"] as? String
                let aFinished = a["finished"] as? Bool
                let name = a["name"] as? String
                let chosen = a["chosen"] as? Int

                let options: [String]? = {
                    if let arr = a["options"] as? [String] { return arr }
                    if let arrAny = a["options"] as? [Any] {
                        let dicts = arrAny.compactMap { $0 as? [String: Any] }
                        let texts = dicts.compactMap { $0["text"] as? String }
                        return texts.isEmpty ? nil : texts
                    }
                    return nil
                }()

                return ActivityAction(
                    id: actionId,
                    type: type,
                    file: file,
                    finished: aFinished,
                    name: name,
                    options: options,
                    chosen: chosen
                )
            }

            return ActivityActionStep(
                id: stepId,
                authorized: authorized,
                finished: finished,
                actions: actions
            )
        }
    }



    
    func extractChoiceSteps(activityName: String) -> [ChoiceStep] {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return [] }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any],
              let steps = payload["steps"] as? [[String: Any]]
        else { return [] }

        return steps.map { s in
            let stepId: String = {
                if let i = s["id"] as? Int { return String(i) }
                return String(describing: s["id"] ?? "")
            }()
            let finished = (s["finished"] as? Bool) ?? false
            let authorized = (s["authorized"] as? Bool) ?? false

            let actionsArr = (s["actions"] as? [[String: Any]]) ?? []
            let actions: [ChoiceAction] = actionsArr.map { a in
                let actionId: String = {
                    if let i = a["id"] as? Int { return String(i) }
                    return String(describing: a["id"] ?? "")
                }()
                let type = (a["type"] as? String) ?? ""

                let file = a["file"] as? String
                let finished = a["finished"] as? Bool

                let name = a["name"] as? String
                let options = (a["options"] as? [String]) ?? []
                let chosen = (a["chosen"] as? Int) ?? -1

                return ChoiceAction(
                    id: actionId,
                    type: type,
                    file: file,
                    finished: finished,
                    name: name,
                    options: options,
                    chosen: chosen
                )
            }

            return ChoiceStep(id: stepId, authorized: authorized, finished: finished, actions: actions)
        }
    }


    func extractSteps(activityName: String) -> [ActivityStep] {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return [] }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any],
              let steps = payload["steps"] as? [[String: Any]]
        else { return [] }

        return steps.map { s in
            ActivityStep(
                id: String(describing: s["id"] ?? ""),
                name: String(describing: s["name"] ?? ""),
                finished: (s["finished"] as? Bool) ?? false
            )
        }
    }


    // MARK: - Finished step

    func parseFinishedStepKey(_ key: String) -> (String, String)? {
        for activity in GlobalDataConfig.allowedActivities {
            let prefix = "\(activity)_finished_step_"
            if key.hasPrefix(prefix) {
                let stepId = String(key.dropFirst(prefix.count))
                return stepId.isEmpty ? nil : (activity, stepId)
            }
        }
        return nil
    }

    func handleFinishedStep(activityName: String, stepId: String, incoming: [String: Any], from session: WebSocketSession) {
        mergeIncomingActivityIntoGlobal(activityName: activityName, incoming: incoming)
        setStepFinishedTrueInGlobal(activityName: activityName, stepId: stepId)
        syncActivityFromGlobalJSON(activityName)
        log("✅ \(activityName) finished step \(stepId) (UI updated)")
    }

    func setStepFinishedTrueInGlobal(activityName: String, stepId: String) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = activities[idx][activityName] as? [String: Any] else { return }
        guard var steps = payload["steps"] as? [[String: Any]] else { return }

        for i in steps.indices {
            let id = String(describing: steps[i]["id"] ?? "")
            if id == stepId {
                steps[i]["finished"] = true
                payload["steps"] = steps
                activities[idx][activityName] = payload
                globalJSON["activity"] = activities
                return
            }
        }
    }

    // MARK: - Sessions stored in global json

    func setSessionIdInGlobal(activityName: String, sessionId: String) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = activities[idx][activityName] as? [String: Any] else { return }

        payload["ws_session_id"] = sessionId
        activities[idx][activityName] = payload
        globalJSON["activity"] = activities
    }

    func attachSession(activityName: String, session: WebSocketSession) {
        sessionByActivity[activityName] = session

        let sid = String(ObjectIdentifier(session).hashValue)
        setSessionIdInGlobal(activityName: activityName, sessionId: sid)

        sessionIdByActivity[activityName] = sid
        activityConnected[activityName] = true
        refreshManualControlsAvailability()
    }

    func getSessionForActivity(_ activityName: String) -> WebSocketSession? {
        sessionByActivity[activityName]
    }

    // MARK: - Choice updates

    func setChosenInGlobal(choiceId: String, chosen: Int) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0["choice_activity"] != nil }) else { return }
        guard var payload = activities[idx]["choice_activity"] as? [String: Any] else { return }
        guard var choices = payload["choices"] as? [[String: Any]] else { return }

        for i in choices.indices {
            let id = String(describing: choices[i]["id"] ?? "")
            if id == choiceId {
                choices[i]["chosen"] = chosen
                payload["choices"] = choices
                activities[idx]["choice_activity"] = payload
                globalJSON["activity"] = activities
                return
            }
        }
    }
    
    func sendKey(_ key: String, to activityName: String) {
        guard let session = getSessionForActivity(activityName) else {
            log("🛑🛑🛑 ERROR: \(activityName) is NOT connected — cannot send \(key) 🛑🛑🛑")
            return
        }

        var payload = globalJSON
        payload["key"] = key

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify payload for key=\(key)")
            return
        }

        log("➡️ Manual send -> \(key) to \(activityName)")
        session.writeText(text)
    }


    // MARK: - Emotions

    func extractEmotionsFromGlobalJSON() -> [EmotionItem] {
        guard let arr = globalJSON["emotions"] as? [[String: Any]] else { return [] }
        return arr.compactMap { e in
            let type = (e["type"] as? String) ?? ""
            guard !type.isEmpty else { return nil }

            let raw = e["level"]
            let level: Double
            if let d = raw as? Double { level = d }
            else if let i = raw as? Int { level = Double(i) }
            else { level = 0 }

            return EmotionItem(type: type, level: min(100, max(0, level)))
        }
    }

    func applyEmotionDeltas(_ deltas: [String: Double]) {
        guard var arr = globalJSON["emotions"] as? [[String: Any]] else { return }

        for i in arr.indices {
            let type = ((arr[i]["type"] as? String) ?? "").lowercased()
            guard let delta = deltas[type] else { continue }

            let raw = arr[i]["level"]
            let current: Double
            if let d = raw as? Double { current = d }
            else if let n = raw as? Int { current = Double(n) }
            else { current = 0 }

            arr[i]["level"] = min(100, max(0, current + delta))
        }

        globalJSON["emotions"] = arr
        emotions = extractEmotionsFromGlobalJSON()
        sendEmotionsUpdateToAtmosphere()
    }

    func sendEmotionsUpdateToAtmosphere() {
        guard let session = getSessionForActivity("jauge_activity") else {
            log("🛑🛑🛑 ERROR: jauge_activity is NOT connected — cannot send update_emotions 🛑🛑🛑")
            return
        }

        var payload = globalJSON
        payload["key"] = "update_emotions"

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify update_emotions payload")
            return
        }

        log("➡️ Sending update_emotions to jauge_activity")
        session.writeText(text)
    }
    
    func handleSequencingIfNeeded(incomingKey: String, incomingJSON: [String: Any]) {
        guard let route = Sequencing.routes[incomingKey] else { return }
        if route.targetActivity == "choice_activity",
           let choiceId = parseChoiceAuthorizationKey(route.outgoingKey) {
            setChoiceAuthorizedInGlobal(choiceId: choiceId, value: true)
        }
        
        if route.targetActivity == "choice_activity",
           let stepId = parseChoiceStepAuthorizationKey(route.outgoingKey) {
            setChoiceStepAuthorizedInGlobal(stepId: stepId, value: true)
        }

        setAuthorizedInGlobal(activityName: route.targetActivity, value: true)

        guard let targetSession = getSessionForActivity(route.targetActivity) else {
            log("🛑🛑🛑 ERROR: sequencing target '\(route.targetActivity)' is NOT connected — cannot send '\(route.outgoingKey)' 🛑🛑🛑")
            return
        }

        var payload = incomingJSON
        payload["key"] = route.outgoingKey

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify sequencing payload")
            return
        }

        log("➡️ Sequencing: '\(incomingKey)' -> send '\(route.outgoingKey)' to \(route.targetActivity) (authorized=true)")
        log("📤 Sequencing payload JSON:\n\(pretty(payload))")
        targetSession.writeText(text)
    }
    
    func forwardIncomingJSON(_ incoming: [String: Any], toActivities: [String], reason: String) {
        guard let text = stringify(json: incoming) else {
            log("❌ Failed to stringify incoming JSON for forward. reason=\(reason)")
            return
        }

        for activity in toActivities {
            guard let session = getSessionForActivity(activity) else {
                log("⚠️ Forward skipped: \(activity) not connected. reason=\(reason)")
                continue
            }
            session.writeText(text)
        }

        log("➡️ Forwarded incoming JSON to \(toActivities.joined(separator: ", ")) reason=\(reason)")
    }
    
    func extractFinished(activityName: String) -> Bool {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return false }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any]
        else { return false }
        return (payload["finished"] as? Bool) ?? false
    }
    
    func setAuthorizedInGlobal(activityName: String, value: Bool) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = activities[idx][activityName] as? [String: Any] else { return }

        payload["authorized"] = value
        activities[idx][activityName] = payload
        globalJSON["activity"] = activities

        // refresh UI status (if you have a sync call)
        syncAllFromGlobalJSON()
    }

    func extractAuthorized(activityName: String) -> Bool {
        guard let activities = globalJSON["activity"] as? [[String: Any]] else { return false }
        guard let obj = activities.first(where: { $0[activityName] != nil }),
              let payload = obj[activityName] as? [String: Any]
        else { return false }
        return (payload["authorized"] as? Bool) ?? false
    }
    
    func setChoiceAuthorizedInGlobal(choiceId: String, value: Bool) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0["choice_activity"] != nil }) else { return }
        guard var payload = activities[idx]["choice_activity"] as? [String: Any] else { return }
        guard var choices = payload["choices"] as? [[String: Any]] else { return }

        for i in choices.indices {
            let id = String(describing: choices[i]["id"] ?? "")
            if id == choiceId {
                choices[i]["authorized"] = value
                payload["choices"] = choices
                activities[idx]["choice_activity"] = payload
                globalJSON["activity"] = activities
                syncActivityFromGlobalJSON("choice_activity")
                return
            }
        }
    }

    func parseChoiceAuthorizationKey(_ key: String) -> String? {
        // "choice_2_authorization" -> "2"
        guard key.hasPrefix("choice_"), key.hasSuffix("_authorization") else { return nil }
        let core = key.dropFirst("choice_".count).dropLast("_authorization".count)
        let id = String(core)
        return id.isEmpty ? nil : id
    }
    
    func startActivity() {
        guard let session = getSessionForActivity("choice_activity") else {
            log("🛑🛑🛑 ERROR: choice_activity is NOT connected — cannot start activity 🛑🛑🛑")
            return
        }
        guard !extractStarted() else { return }

        // ✅ mark started in global json
        globalJSON["started"] = true
        activityStarted = true

        setChoiceStepAuthorizedInGlobal(stepId: "1", value: true)

        // update button state
        canStartActivity = false

        var payload = globalJSON
        // payload["key"] = "choice_activity_step_1_authorization"
        payload["key"] = "choice_activity_step_1_authorization"

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify startActivity payload")
            return
        }

        log("➡️ Manual START ACTIVITY -> send choice_1_authorization to choice_activity (started=true)")
        session.writeText(text)
    }

    
    func refreshManualControlsAvailability() {
        canStartActivity = (getSessionForActivity("choice_activity") != nil)
    }
    func extractStarted() -> Bool {
        (globalJSON["started"] as? Bool) ?? false
    }
    
    func parseChoiceVideoFinishedKey(_ key: String) -> (String, String)? {
        // "choice_activity_step_{step_id}_{action_id}_finished"
        guard key.hasPrefix("choice_activity_step_"),
              key.hasSuffix("_finished")
        else { return nil }

        let core = key
            .dropFirst("choice_activity_step_".count)
            .dropLast("_finished".count)

        let parts = core.split(separator: "_")
        guard parts.count == 2 else { return nil }

        return (String(parts[0]), String(parts[1]))
    }

    func parseChoiceSelectedKey(_ key: String) -> (String, String, Int)? {
        // "choice_activity_{step_id}_{action_id}_{selected}"
        // split -> ["choice","activity","{step}","{action}","{selected}"]
        let parts = key.split(separator: "_")
        guard parts.count == 5 else { return nil }
        guard parts[0] == "choice", parts[1] == "activity" else { return nil }

        let stepId = String(parts[2])
        let actionId = String(parts[3])
        guard let selected = Int(parts[4]) else { return nil }
        guard selected == -1 || selected == 0 || selected == 1 else { return nil }

        return (stepId, actionId, selected)
    }

    func handleChoiceVideoActionFinished(stepId: String, actionId: String, incoming: [String: Any], from session: WebSocketSession) {
        // le client a déjà mis finished=true, mais on merge + sécurité + refresh UI
        mergeIncomingActivityIntoGlobal(activityName: "choice_activity", incoming: incoming)
        setChoiceVideoFinishedTrueInGlobal(stepId: stepId, actionId: actionId)
        syncActivityFromGlobalJSON("choice_activity")
        log("✅ choice_activity step \(stepId) action \(actionId) video finished=true (UI updated)")
    }
    
    func authorizeStep(activityName: String, stepId: String) {
        guard let session = getSessionForActivity(activityName) else {
            log("🛑🛑🛑 ERROR: \(activityName) is NOT connected — cannot authorize step \(stepId) 🛑🛑🛑")
            return
        }

        setStepAuthorizedInGlobal(activityName: activityName, stepId: stepId, value: true)

        var payload = globalJSON
        payload["key"] = "\(activityName)_step_\(stepId)_authorization"

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify step authorization payload")
            return
        }

        log("➡️ Manual authorize -> send \(activityName)_step_\(stepId)_authorization to \(activityName)")
        session.writeText(text)
    }

    func setStepAuthorizedInGlobal(activityName: String, stepId: String, value: Bool) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0[activityName] != nil }) else { return }
        guard var payload = activities[idx][activityName] as? [String: Any] else { return }
        guard var steps = payload["steps"] as? [[String: Any]] else { return }

        for i in steps.indices {
            let sid = String(describing: steps[i]["id"] ?? "")
            if sid == stepId {
                steps[i]["authorized"] = value
                payload["steps"] = steps
                activities[idx][activityName] = payload
                globalJSON["activity"] = activities
                syncActivityFromGlobalJSON(activityName)
                return
            }
        }
    }


    func handleChoiceSelected(stepId: String, actionId: String, selected: Int, incoming: [String: Any], from session: WebSocketSession) {
        mergeIncomingActivityIntoGlobal(activityName: "choice_activity", incoming: incoming)
        setChoiceChosenInGlobal(stepId: stepId, actionId: actionId, chosen: selected)
        syncActivityFromGlobalJSON("choice_activity")
        log("✅ choice_activity step \(stepId) action \(actionId) choice chosen=\(selected) (UI updated)")
    }
    
    
    private func idString(_ any: Any?) -> String {
        if let i = any as? Int { return String(i) }
        if let s = any as? String { return s }
        return String(describing: any ?? "")
    }

    private func setChoiceVideoFinishedTrueInGlobal(stepId: String, actionId: String) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0["choice_activity"] != nil }) else { return }
        guard var payload = activities[idx]["choice_activity"] as? [String: Any] else { return }
        guard var steps = payload["steps"] as? [[String: Any]] else { return }

        for sIndex in steps.indices {
            if idString(steps[sIndex]["id"]) == stepId {
                guard var actions = steps[sIndex]["actions"] as? [[String: Any]] else { break }

                for aIndex in actions.indices {
                    if idString(actions[aIndex]["id"]) == actionId {
                        actions[aIndex]["finished"] = true
                        steps[sIndex]["actions"] = actions
                        payload["steps"] = steps
                        activities[idx]["choice_activity"] = payload
                        globalJSON["activity"] = activities
                        return
                    }
                }
            }
        }
    }

    private func setChoiceChosenInGlobal(stepId: String, actionId: String, chosen: Int) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0["choice_activity"] != nil }) else { return }
        guard var payload = activities[idx]["choice_activity"] as? [String: Any] else { return }
        guard var steps = payload["steps"] as? [[String: Any]] else { return }

        for sIndex in steps.indices {
            if idString(steps[sIndex]["id"]) == stepId {
                guard var actions = steps[sIndex]["actions"] as? [[String: Any]] else { break }

                for aIndex in actions.indices {
                    if idString(actions[aIndex]["id"]) == actionId {
                        actions[aIndex]["chosen"] = chosen
                        steps[sIndex]["actions"] = actions
                        payload["step"] = steps
                        activities[idx]["choice_activity"] = payload
                        globalJSON["activity"] = activities
                        return
                    }
                }
            }
        }
    }
    
    func parseChoiceStepAuthorizationKey(_ key: String) -> String? {
        // "choice_2_authorization" -> "2"
        guard key.hasPrefix("choice_"), key.hasSuffix("_authorization") else { return nil }
        let core = key.dropFirst("choice_".count).dropLast("_authorization".count)
        let stepId = String(core)
        return stepId.isEmpty ? nil : stepId
    }

    func setChoiceStepAuthorizedInGlobal(stepId: String, value: Bool) {
        guard var activities = globalJSON["activity"] as? [[String: Any]] else { return }
        guard let idx = activities.firstIndex(where: { $0["choice_activity"] != nil }) else { return }
        guard var payload = activities[idx]["choice_activity"] as? [String: Any] else { return }
        guard var steps = payload["steps"] as? [[String: Any]] else { return }

        for i in steps.indices {
            let sid = idString(steps[i]["id"])
            if sid == stepId {
                steps[i]["authorized"] = value
                payload["steps"] = steps
                activities[idx]["choice_activity"] = payload
                globalJSON["activity"] = activities
                syncActivityFromGlobalJSON("choice_activity") // ✅ refresh UI
                return
            }
        }
    }

    func parseChoiceStepFinishedKey(_ key: String) -> String? {
        // "choice_activity_step_<step_id>_finished"
        guard key.hasPrefix("choice_activity_step_"),
              key.hasSuffix("_finished")
        else { return nil }

        let core = key
            .dropFirst("choice_activity_step_".count)
            .dropLast("_finished".count)

        let stepId = String(core)
        return stepId.isEmpty ? nil : stepId
    }

    func handleChoiceStepFinished(stepId: String, incoming: [String: Any], from session: WebSocketSession) {
        // client already set finished=true, but we merge + refresh UI
        mergeIncomingActivityIntoGlobal(activityName: "choice_activity", incoming: incoming)
        syncActivityFromGlobalJSON("choice_activity")
        log("✅ choice_activity step \(stepId) finished=true (UI updated, dot -> red)")
    }
    
    // MARK: - Manual authorization (UI buttons)

    func authorizeActivity(activityName: String) {
        guard let session = getSessionForActivity(activityName) else {
            log("🛑🛑🛑 ERROR: \(activityName) is NOT connected — cannot send start_authorization 🛑🛑🛑")
            return
        }

        // set authorized=true in global json
        setAuthorizedInGlobal(activityName: activityName, value: true)

        var payload = globalJSON
        payload["key"] = "start_authorization"

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify start_authorization payload")
            return
        }

        log("➡️ Manual authorize -> send start_authorization to \(activityName)")
        session.writeText(text)
    }

    func authorizeChoiceStep(stepId: String) {
        guard let session = getSessionForActivity("choice_activity") else {
            log("🛑🛑🛑 ERROR: choice_activity is NOT connected — cannot authorize step \(stepId) 🛑🛑🛑")
            return
        }

        // set step.authorized=true in global json
        setChoiceStepAuthorizedInGlobal(stepId: stepId, value: true)

        var payload = globalJSON
        payload["key"] = "choice_activity_step_\(stepId)_authorization"

        guard let text = stringify(json: payload) else {
            log("❌ Failed to stringify choice step authorization payload")
            return
        }

        log("➡️ Manual authorize -> send choice_activity_step_\(stepId)_authorization to choice_activity")
        session.writeText(text)
    }


}

// MARK: - Helpers (file-level)

  func makeWSAddress(ip: String?, port: Int) -> String {
    let host = (ip?.isEmpty == false) ? ip! : "127.0.0.1"
    return "ws://\(host):\(port)"
}

  func stringify(json: [String: Any]) -> String? {
    guard let data = try? JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted]),
          let text = String(data: data, encoding: .utf8)
    else { return nil }
    return text
}

  func firstIPv4AddressNonLoopback() -> String? {
    var address: String?

    var ifaddr: UnsafeMutablePointer<ifaddrs>?
    guard getifaddrs(&ifaddr) == 0, let firstAddr = ifaddr else { return nil }
    defer { freeifaddrs(ifaddr) }

    for ptr in sequence(first: firstAddr, next: { $0.pointee.ifa_next }) {
        let interface = ptr.pointee
        let family = interface.ifa_addr.pointee.sa_family
        if family == UInt8(AF_INET) {
            let name = String(cString: interface.ifa_name)
            if name == "lo0" { continue }

            var hostname = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            let success = getnameinfo(
                interface.ifa_addr,
                socklen_t(interface.ifa_addr.pointee.sa_len),
                &hostname,
                socklen_t(hostname.count),
                nil,
                0,
                NI_NUMERICHOST
            )
            if success == 0 {
                let ip = String(cString: hostname)
                if !ip.hasPrefix("127.") {
                    address = ip
                    break
                }
            }
        }
    }
    return address
}
