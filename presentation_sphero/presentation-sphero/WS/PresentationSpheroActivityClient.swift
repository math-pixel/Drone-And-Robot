// PresentationSpheroActivityClient.swift
import Foundation
import Starscream

final class PresentationSpheroActivityClient: NSObject, WebSocketDelegate {

    private var socket: WebSocket?
    private let url: URL

    // State
    private var isConnected = false
    private var isConnecting = false
    private var shouldAutoReconnect = true

    // Timers
    private var pingTimer: Timer?
    private var reconnectTimer: Timer?

    // Callbacks
    var onMessage: (([String: Any]) -> Void)?
    var onConnectionState: ((Bool) -> Void)?

    init(wsURL: String) {
        self.url = URL(string: wsURL)!
        super.init()
    }

    func connect() {
        shouldAutoReconnect = true
        connectInternal()
    }

    func disconnect() {
        shouldAutoReconnect = false
        stopPing()
        stopReconnectLoop()

        isConnected = false
        isConnecting = false

        socket?.disconnect()
        socket = nil

        onConnectionState?(false)
    }

    func send(json: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: json),
              let text = String(data: data, encoding: .utf8)
        else { return }

        socket?.write(string: text)
    }

    // MARK: - Private

    private func connectInternal() {
        guard !isConnected, !isConnecting else { return }
        isConnecting = true

        // Always recreate a fresh socket
        var request = URLRequest(url: url)
        request.timeoutInterval = 5

        let ws = WebSocket(request: request)
        ws.delegate = self

        socket = ws
        ws.connect()
    }

    private func startPing() {
        stopPing()
        pingTimer = Timer.scheduledTimer(withTimeInterval: 4, repeats: true) { [weak self] _ in
            guard let self else { return }
            self.socket?.write(ping: Data())
        }
    }

    private func stopPing() {
        pingTimer?.invalidate()
        pingTimer = nil
    }

    private func startReconnectLoop() {
        guard shouldAutoReconnect else { return }
        guard reconnectTimer == nil else { return }

        reconnectTimer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            guard let self else { return }
            if !self.isConnected {
                self.connectInternal()
            }
        }
    }

    private func stopReconnectLoop() {
        reconnectTimer?.invalidate()
        reconnectTimer = nil
    }

    private func setConnected(_ value: Bool) {
        isConnected = value
        onConnectionState?(value)
    }

    // MARK: - WebSocketDelegate

    func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        switch event {

        case .connected:
            isConnecting = false
            setConnected(true)
            stopReconnectLoop()
            startPing()
            print("🟢 WS connected")

        case .text(let text):
            if let data = text.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                onMessage?(json)
            }

        case .disconnected(let reason, _):
            isConnecting = false
            setConnected(false)
            stopPing()
            print("🔴 WS disconnected:", reason)
            startReconnectLoop()

        case .error(let error):
            isConnecting = false
            setConnected(false)
            stopPing()
            print("❌ WS error:", error?.localizedDescription ?? "")
            startReconnectLoop()

        case .cancelled:
            isConnecting = false
            setConnected(false)
            stopPing()
            print("⚠️ WS cancelled")
            startReconnectLoop()

        default:
            break
        }
    }
}
