import Foundation
import SwiftUI
import Swifter
import Combine

@MainActor
final class ServerManager: ObservableObject {
    @Published var isRunning: Bool = false
    @Published var localIPAddress: String?
    @Published var wsServerAddress: String?
    @Published var logs: [String] = []
    @Published var activitySteps: [String: [ActivityStep]] = [:]
    @Published var activityOrder: [String] = []
    @Published var emotions: [EmotionItem] = []
    @Published var sessionIdByActivity: [String: String] = [:]
    @Published var activityConnected: [String: Bool] = [:]
    @Published var activityAuthorized: [String: Bool] = [:]
    @Published var activityFinished: [String: Bool] = [:]
    @Published var canStartActivity: Bool = false
    @Published var activityStarted: Bool = false
    @Published var choiceStepsByActivity: [String: [ChoiceStep]] = [:]
    @Published var activityActionSteps: [String: [ActivityActionStep]] = [:]

    // Server
    let server = HttpServer()
    let port: Int = 8057
    let wsRoute: String = "/ws"
    var routesAdded = false

    // Sessions
    var sessions = Set<ObjectIdentifier>()
    var sessionMap: [ObjectIdentifier: WebSocketSession] = [:]
    var sessionActivity: [ObjectIdentifier: String] = [:]
    var sessionByActivity: [String: WebSocketSession] = [:]

    // Central JSON state
    var globalJSON: [String: Any] = [:]

    // MARK: - Logs

    func clearLogs() { logs.removeAll() }

    func log(_ msg: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "[\(ts)] \(msg)"
        logs.append(line)
        print(line)
    }

    // MARK: - Public

    func start() {
        guard !isRunning else { return }

        localIPAddress = firstIPv4AddressNonLoopback() ?? "127.0.0.1"
        wsServerAddress = makeWSAddress(ip: localIPAddress, port: port)

        globalJSON = GlobalDataConfig.makeInitialGlobalJSON(wsServerAddress: wsServerAddress ?? "ws://127.0.0.1:\(port)")
        globalJSON["key"] = "" // ne jamais garder identification_request en global state

        activityOrder = extractActivityOrderFromGlobalJSON()
        syncAllFromGlobalJSON()

        if !routesAdded {
            addRoutes()
            routesAdded = true
        }

        do {
            server["/ping"] = { [weak self] req in
                self?.log("HTTP /ping from \(req.address ?? "unknown")")
                return .ok(.text("pong"))
            }

            try server.start(in_port_t(port))
            isRunning = true
            log("✅ Server STARTED")
            log("   HTTP: http://127.0.0.1:\(port)/ping")
            log("   WS:   ws://127.0.0.1:\(port)\(wsRoute)")
            log("   LAN:  \(wsServerAddress ?? "-")\(wsRoute)")
        } catch {
            isRunning = false
            log("❌ Swifter start error: \(error.localizedDescription)")
        }
    }

    func stop() {
        guard isRunning else { return }

        server.stop()
        isRunning = false
        log("🛑 Server STOPPED")

        sessions.removeAll()
        sessionMap.removeAll()
        sessionActivity.removeAll()
        sessionByActivity.removeAll()
        refreshManualControlsAvailability()

        sessionIdByActivity.removeAll()
        activityConnected.removeAll()

        setAllConnectedFalseInGlobal()
        syncAllFromGlobalJSON()
    }
}


