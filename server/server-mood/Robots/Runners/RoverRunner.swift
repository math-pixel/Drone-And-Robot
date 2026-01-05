// RoverRunner.swift — change ONLY the selector + hardcode the name used by your app.
import Foundation
import Pappe

final class RoverRunner {

    unowned let robot: Robot

    private let engine = SyncsEngine()
    private var controller: SyncsController?
    private var config: SyncsControllerConfig?

    var pendingCommand: RobotCommand?

    init(robot: Robot) {
        self.robot = robot
    }

    func connect() {

        // ✅ Synchrosphere public docs show .anyRVR as the selector entrypoint.
        // If your Synchrosphere version exposes a "by name" selector, replace this line accordingly.
        // Example (IF available in your version):
        // var cfg = SyncsControllerConfig(deviceSelector: .rvr(named: robot.bluetoothName))
        var cfg = SyncsControllerConfig(deviceSelector: .anyRVR)

        cfg.stateDidChangeCallback = { [weak self] state in
            guard let self = self else { return }

            if state.contains(.isAwake) && !self.robot.isConnected {
                DispatchQueue.main.async { self.robot._didConnect() }
            }
            if !state.contains(.isConnected) && self.robot.isConnected {
                DispatchQueue.main.async { self.robot._didDisconnect() }
            }
        }

        self.config = cfg

        controller = engine.makeController(for: cfg) { names, ctx in
            activity(names.Main, [
                "cmdSpeed","cmdHeading","cmdDir","doRoll","doStop","cmdDuration","cmdLeftWheel","cmdRightWheel","doRaw",
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

                        guard let cmd = self.pendingCommand else { return }

                        switch cmd {
                        case .forward(let speed, let durationS):
                            val.cmdSpeed = SyncsSpeed(UInt16(speed))
                            val.cmdHeading = SyncsHeading(UInt16(self.robot.heading))
                            val.cmdDir = SyncsDir.forward
                            val.doRoll = true
                            val.cmdDuration = durationS

                        case .backward(let speed, let durationS):
                            val.cmdSpeed = SyncsSpeed(UInt16(speed))
                            val.cmdHeading = SyncsHeading(UInt16(self.robot.heading))
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
                            // We'll reuse RollForSeconds with opposite directions by heading trick is not possible.
                            // So we call RawMotor if available; if not, this won't compile in your Syncs version.
                            // ✅ Use RawMotor when present:
                            val.doRoll = false
                            val.doStop = false
                            val.doRaw = true

                        case .stop:
                            val.cmdHeading = SyncsHeading(UInt16(self.robot.heading))
                            val.doStop = true
                        }

                        self.pendingCommand = nil
                    }

                    `if` { val.doRoll as Bool } then: {
                        run(Syncs.RollForSeconds, [val.cmdSpeed, val.cmdHeading, val.cmdDir, val.cmdDuration])
                    }

                    `if` { val.doStop as Bool } then: {
                        run(Syncs.StopRoll, [val.cmdHeading])
                    }

                    //`if` { val.doRaw as Bool } then: {
                    //    run(Syncs.DriveRawMotor, [
                    //        val.cmdLeftWheel,
                    //        val.cmdRightWheel,
                    //        val.cmdDuration
                    //    ])
                    //}
                    
                    run(Syncs.WaitMilliseconds, [10])
                } until: { false }
            }
        }

        controller?.start()
    }

    func disconnect() {
        controller?.stop()
        controller = nil
    }

    func send(_ command: RobotCommand) {
        pendingCommand = command
    }
}
