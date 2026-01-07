import Foundation
import Combine

@MainActor
final class RoverControlManager: ObservableObject {
    @Published private(set) var isConnected: Bool = false

    private let bluetoothName: String = "RV-4531"
    private var rover: Rover?

    private var pollTask: Task<Void, Never>?
    private var roverObserver: Any?

    private func startObservingWSCommands() {
        stopObservingWSCommands()

        roverObserver = NotificationCenter.default.addObserver(
            forName: .roverWSCommand,
            object: nil,
            queue: .main
        ) { [weak self] note in
            guard let self else { return }
            guard let key = note.userInfo?["key"] as? String else { return }
            self.handleParsedWSKey(key)
        }
    }

    private func stopObservingWSCommands() {
        if let roverObserver {
            NotificationCenter.default.removeObserver(roverObserver)
            self.roverObserver = nil
        }
    }

    func toggleConnection() {
        if let rover, rover.isConnected {
            rover.disconnect()
            self.rover = nil
            isConnected = false
            stopPolling()
            stopObservingWSCommands()
        } else {
            let r = Rover(bluetoothName: bluetoothName)
            rover = r
            r.connect()
            startPolling()
            startObservingWSCommands()
        }
    }

    // Public commands (UI can still call these)
    func forward()  { rover?.forward(speed: 10) }
    func backward() { rover?.backward(speed: 80) }
    func left()     { rover?.turn(degrees: -20) }
    func right()    { rover?.turn(degrees: 20) }
    func stop()     { rover?.stop() }

    private func handleParsedWSKey(_ key: String) {
        // rover_stop
        if key == "rover_stop" {
            stop()
            return
        }

        // rover_<forward|backward>_<speed>_<duration>
        // rover_<right|left>_<degrees>
        let parts = key.split(separator: "_").map(String.init)
        guard parts.count >= 2, parts[0] == "rover" else { return }

        let action = parts[1]

        switch action {
        case "forward", "backward":
            guard parts.count >= 4,
                  let speed = Int(parts[2]),
                  let duration = Int(parts[3]) else { return }

            if action == "forward" {
                rover?.forward(speed: speed, durationS: duration)
            } else {
                rover?.backward(speed: speed, durationS: duration)
            }

        case "left", "right":
            guard parts.count >= 3,
                  let degrees = Int(parts[2]) else { return }

            let signedDegrees = (action == "left") ? -abs(degrees) : abs(degrees)
            rover?.turn(degrees: signedDegrees)

        default:
            return
        }
    }

    private func startPolling() {
        stopPolling()
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                await MainActor.run {
                    self?.isConnected = self?.rover?.isConnected ?? false
                }
                try? await Task.sleep(nanoseconds: 200_000_000)
            }
        }
    }

    private func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }
}
