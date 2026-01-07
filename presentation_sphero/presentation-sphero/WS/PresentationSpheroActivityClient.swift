// PresentationSpheroActivityClient.swift
import Foundation
import Starscream

final class PresentationSpheroActivityClient: NSObject, WebSocketDelegate {

    private var socket: WebSocket?
    private let url: URL

    var onMessage: (([String: Any]) -> Void)?

    init(wsURL: String) {
        self.url = URL(string: wsURL)!
        super.init()
    }

    func connect() {
        var request = URLRequest(url: url)
        request.timeoutInterval = 5
        socket = WebSocket(request: request)
        socket?.delegate = self
        socket?.connect()
    }

    func disconnect() {
        socket?.disconnect()
    }

    func send(json: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: json),
              let text = String(data: data, encoding: .utf8)
        else { return }

        socket?.write(string: text)
    }

    // MARK: - WebSocketDelegate
    func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        switch event {

        case .connected:
            print("🟢 WS connected")

        case .text(let text):
            if let data = text.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                onMessage?(json)
            }

        case .disconnected(let reason, _):
            print("🔴 WS disconnected:", reason)

        case .error(let error):
            print("❌ WS error:", error?.localizedDescription ?? "")

        default:
            break
        }
    }
}
