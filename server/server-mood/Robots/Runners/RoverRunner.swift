// RoverRunner.swift — change ONLY the selector + hardcode the name used by your app.
import Foundation
import Pappe
final class RoverRunner {

    weak var robot: Robot?   // ✅ was: unowned let robot: Robot

    private let engine = SyncsEngine()
    private var controller: SyncsController?
    private var config: SyncsControllerConfig?

    var pendingCommand: RobotCommand?

    init(robot: Robot) {
        self.robot = robot
    }

    func connect() {
        var cfg = SyncsControllerConfig(deviceSelector: .anyRVR)

        cfg.stateDidChangeCallback = { [weak self] state in
            guard let self, let robot = self.robot else { return }

            if state.contains(.isAwake) && !robot.isConnected {
                DispatchQueue.main.async { robot._didConnect() }
            }

            if !state.contains(.isConnected) && robot.isConnected {
                DispatchQueue.main.async { robot._didDisconnect() }
            }
        }

        // ✅ Remplace UNIQUEMENT le builder de makeController par ça (plus de return/guard dans le result builder)

        self.config = cfg

        guard let robot = self.robot else { return } // ✅ hors du builder (ok)

        controller = engine.makeController(for: cfg) { [weak self, weak robot] names, ctx in
            activity(names.Main, [
                "cmdSpeed","cmdHeading","cmdDir","doRoll","doStop","cmdDuration",
                "cmdLeftWheel","cmdRightWheel","doRaw",
            ]) { val in

                exec {
                    val.cmdSpeed = SyncsSpeed(0)
                    val.cmdHeading = SyncsHeading(0)
                    val.cmdDir = SyncsDir.forward
                    val.doRoll = false
                    val.doStop = false
                    val.cmdDuration = 1
                    val.cmdLeftWheel = SyncsSpeed(0)
                    val.cmdRightWheel = SyncsSpeed(0)
                    val.doRaw = false
                }

                `repeat` {
                    exec {
                        val.doRoll = false
                        val.doStop = false
                        val.doRaw = false

                        guard let cmd = self?.pendingCommand else { return }

                        switch cmd {
                        case .forward(let speed, let durationS):
                            val.cmdSpeed = SyncsSpeed(UInt16(speed))
                            val.cmdHeading = SyncsHeading(0)
                            val.cmdDir = SyncsDir.forward

                            val.doRoll = true
                            val.cmdDuration = durationS

                        case .backward(let speed, let durationS):
                            val.cmdSpeed = SyncsSpeed(UInt16(speed))
                            val.cmdHeading = SyncsHeading(0)
                            val.cmdDir = SyncsDir.backward
                            val.doRoll = true
                            val.cmdDuration = durationS

                        case .turn(let heading, let durationS):
                            val.cmdSpeed = SyncsSpeed(0)
                            val.cmdHeading = SyncsHeading(UInt16(heading))
                            val.cmdDir = SyncsDir.forward
                            val.doRoll = true
                            val.cmdDuration = durationS

                        case .rawWheels(let left, let right, let durationS):
                            val.cmdLeftWheel = SyncsSpeed(UInt16(max(0, left)))
                            val.cmdRightWheel = SyncsSpeed(UInt16(max(0, right)))
                            val.cmdDuration = durationS
                            val.doRaw = true

                        case .stop:
                            val.cmdHeading = SyncsHeading(0)
                            val.doStop = true
                        }

                        self?.pendingCommand = nil
                    }

                    `if` { val.doRoll as Bool } then: {
                        run(Syncs.ResetHeading, [])
                        run(Syncs.RollForSeconds, [val.cmdSpeed, val.cmdHeading, val.cmdDir, val.cmdDuration])
                    }

                    `if` { val.doStop as Bool } then: {
                        run(Syncs.StopRoll, [val.cmdHeading])
                    }

                    run(Syncs.WaitMilliseconds, [10])

                } until: { false }
            }
        }

        controller?.start()

    }

    func disconnect() {
        controller?.stop()
        controller = nil
        pendingCommand = nil
    }

    func send(_ command: RobotCommand) {
        pendingCommand = command
    }
}
