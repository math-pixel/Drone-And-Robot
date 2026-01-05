import Foundation
import Starscream

final class StarscreamSender: NSObject, WebSocketDelegate {

    private var socket: WebSocket?
    private var textToSend: String?

    static func send(text: String, to wsAddress: String) {
        let sender = StarscreamSender()
        sender._send(text: text, to: wsAddress)
    }

    private func _send(text: String, to wsAddress: String) {
        guard let url = URL(string: wsAddress) else { return }

        var request = URLRequest(url: url)
        request.timeoutInterval = 4

        let ws = WebSocket(request: request)
        ws.delegate = self

        self.socket = ws
        self.textToSend = text
        ws.connect()
    }

    func didReceive(event: WebSocketEvent, client: WebSocketClient) {
        switch event {
        case .connected:
            if let text = textToSend {
                client.write(string: text)
            }
            client.disconnect()

        case .disconnected, .error:
            socket = nil
            textToSend = nil

        default:
            break
        }
    }
}
