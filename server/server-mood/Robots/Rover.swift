import Foundation
import Pappe

final class Rover: Robot {

    internal var runner: RoverRunner?

    override init(bluetoothName: String) {
        super.init(bluetoothName: bluetoothName)
        self.runner = RoverRunner(robot: self)
    }

    override func connect() {
        runner?.connect()
    }

    override func disconnect() {
        runner?.disconnect()
    }

    // Keep old overrides (used by UI manager etc.)
    override func forward(speed: Int) {
        runner?.send(.forward(speed: speed, durationS: 3))
    }

    override func backward(speed: Int) {
        runner?.send(.backward(speed: speed, durationS: 2))
    }

    override func turn(degrees: Int) {
        heading = (heading + degrees) % 360
        if heading < 0 { heading += 360 }
        runner?.send(.turn(heading: heading, durationS: 1))
    }

    override func stop() {
        runner?.send(.stop)
    }

    // WS versions (speed + duration)
    func forward(speed: Int, durationS: Int) {
        runner?.send(.forward(speed: speed, durationS: durationS))
    }

    func backward(speed: Int, durationS: Int) {
        runner?.send(.backward(speed: speed, durationS: durationS))
    }
}
