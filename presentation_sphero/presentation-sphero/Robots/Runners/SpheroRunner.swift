//
//  SpheroRunner.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 02/12/2025.
//

import Foundation
import Pappe

/// Runner dedicated to Sphero-like devices (Mini / Bolt).
/// - Uses Synchrosphere + Pappe.
/// - Executes pending commands synchronously in the Pappe loop.
/// - Streams sensors and forwards samples to `Robot` via `_updateFrom(syncsSample:)`.
final class SpheroRunner {

    // MARK: - Properties

    unowned let robot: Robot

    private let engine = SyncsEngine()
    private var controller: SyncsController?
    private var config: SyncsControllerConfig?

    /// Next command to execute (nil = idle)
    var pendingCommand: RobotCommand?

    // MARK: - Init

    init(robot: Robot) {
        self.robot = robot
    }

    // MARK: - Connect

    func connect() {

        //------------------------------------------------------
        // 1) Configure controller (logs + callbacks)
        //------------------------------------------------------

        // Auto selector based on the expected BLE name prefix:
        // - "SB-" => Bolt
        // - "SM-" => Mini
        // fallback => Mini
        let selector: SyncsDeviceSelector = {
            let name = robot.bluetoothName.trimmingCharacters(in: .whitespacesAndNewlines)
            if !name.isEmpty {
                return .named(name)
            }

            // fallback legacy behavior
            let up = robot.bluetoothName.uppercased()
            if up.hasPrefix("SB-") { return .anyBolt }
            if up.hasPrefix("SM-") { return .anyMini }
            return .anyMini
        }()

        var cfg = SyncsControllerConfig(deviceSelector: selector)
        cfg.logLevel = .info
        cfg.triggerMode = .timeAndEvents
        cfg.tickFrequency = 10

        cfg.stateDidChangeCallback = { [weak self] state in
            guard let self = self else { return }

            if state.contains(.isAwake), !self.robot.isConnected {
                DispatchQueue.main.async { self.robot._didConnect() }
            }

            if !state.contains(.isConnected), self.robot.isConnected {
                DispatchQueue.main.async { self.robot._didDisconnect() }
            }

            if state.contains(.isBatteryCritical) {
                DispatchQueue.main.async { self.robot._updateBattery(from: .critical) }
            } else if state.contains(.isBatteryLow) {
                DispatchQueue.main.async { self.robot._updateBattery(from: .low) }
            } else if state.contains(.isConnected) {
                DispatchQueue.main.async { self.robot._updateBattery(from: .ok) }
            } else {
                DispatchQueue.main.async { self.robot._updateBattery(from: nil) }
            }
        }

        self.config = cfg

        //------------------------------------------------------
        // 2) Build Pappe controller
        //------------------------------------------------------
        controller = engine.makeController(for: cfg) { names, ctx in

            activity(names.Main, [
                // command vars
                "cmdSpeed",
                "cmdHeading",
                "cmdDir",
                "cmdSeconds",
                "doRollForSeconds",
                "doStop",

                // sensor vars
                "sensorFrequency",
                "sensorMask",
                "sample",
                "lastSampleTs"
            ]) { val in

                //------------------------------------------------------
                // Initialize Pappe vars once
                //------------------------------------------------------
                exec {
                    // command init
                    val.cmdSpeed = SyncsSpeed(0)
                    val.cmdHeading = SyncsHeading(0)
                    val.cmdDir = SyncsDir.forward
                    val.cmdSeconds = 1
                    val.doRollForSeconds = false
                    val.doStop = false

                    // sensor init
                    val.sensorFrequency = 10
                    val.sensorMask = (SyncsSensors.location
                                      .union(.velocity)
                                      .union(.acceleration)
                                      .union(.yaw))
                    val.sample = SyncsSample.unset
                    val.lastSampleTs = UInt64(0)
                }

                //------------------------------------------------------
                // Run sensors + commands in parallel
                //------------------------------------------------------
                cobegin {

                    // 1) Sensor streamer (updates val.sample continuously)
                    with (.weak) {
                        run(Syncs.SensorStreamer, [
                            val.sensorFrequency,
                            val.sensorMask
                        ], [
                            val.loc.sample
                        ])
                    }

                    // 2) Main loop (consume commands + forward samples to Swift)
                    with {
                        `repeat` {

                            //------------------------------------------------------
                            // A) Forward sensor sample to Swift when it changes
                            //------------------------------------------------------
                            exec {
                                let s: SyncsSample = val.sample
                                let lastTs: UInt64 = val.lastSampleTs

                                // only forward when we have a real sample and timestamp changed
                                if s.timestamp != 0, s.timestamp != lastTs {
                                    val.lastSampleTs = s.timestamp
                                    DispatchQueue.main.async {
                                        self.robot._updateFrom(syncsSample: s)
                                    }
                                }
                            }

                            //------------------------------------------------------
                            // B) SWIFT → PAPPE binding (allowed here)
                            //------------------------------------------------------
                            exec {
                                // Reset flags
                                val.doRollForSeconds = false
                                val.doStop = false

                                guard let cmd = self.pendingCommand else { return }

                                func clampSpeed(_ s: Int) -> SyncsSpeed {
                                    let v = max(0, min(255, s))
                                    return SyncsSpeed(UInt8(v))
                                }

                                func clampHeading(_ h: Int) -> SyncsHeading {
                                    let norm = ((h % 360) + 360) % 360
                                    return SyncsHeading(UInt16(norm))
                                }

                                // Defaults
                                var speed: SyncsSpeed = 0
                                var heading: SyncsHeading = clampHeading(self.robot.heading)
                                var dir: SyncsDir = .forward
                                var seconds: Int = 1
                                var shouldRoll = false
                                var shouldStop = false

                                switch cmd {

                                case .forward(let s, let durationS):
                                    speed = clampSpeed(s)
                                    heading = clampHeading(self.robot.heading)
                                    dir = .forward
                                    seconds = max(1, durationS)
                                    shouldRoll = true

                                case .backward(let s, let durationS):
                                    speed = clampSpeed(s)
                                    heading = clampHeading(self.robot.heading)
                                    dir = .backward
                                    seconds = max(1, durationS)
                                    shouldRoll = true

                                case .turn(let headingDeg, let durationS):
                                    // Keep it simple: roll with speed 0 towards new heading for a moment
                                    speed = clampSpeed(0)
                                    heading = clampHeading(headingDeg)
                                    dir = .forward
                                    seconds = max(1, durationS)
                                    shouldRoll = true

                                case .stop:
                                    heading = clampHeading(self.robot.heading)
                                    shouldStop = true

                                }

                                // Write Pappe vars
                                val.cmdSpeed = speed
                                val.cmdHeading = heading
                                val.cmdDir = dir
                                val.cmdSeconds = seconds
                                val.doRollForSeconds = shouldRoll
                                val.doStop = shouldStop

                                // Consume command
                                self.pendingCommand = nil
                            }

                            //------------------------------------------------------
                            // C) PAPPE execution (no Swift here)
                            //------------------------------------------------------
                            `if` { val.doRollForSeconds as Bool } then: {
                                run(Syncs.RollForSeconds, [
                                    val.cmdSpeed,
                                    val.cmdHeading,
                                    val.cmdDir,
                                    val.cmdSeconds
                                ])
                            }

                            `if` { val.doStop as Bool } then: {
                                run(Syncs.StopRoll, [
                                    val.cmdHeading
                                ])
                            }

                            // Pace
                            run(Syncs.WaitMilliseconds, [10])

                        } until: { false }
                    }
                }
            }
        }

        //------------------------------------------------------
        // 3) Start
        //------------------------------------------------------
        controller?.start()
    }

    // MARK: - Disconnect

    func disconnect() {
        controller?.stop()
        controller = nil
    }

    // MARK: - Commands

    func send(_ command: RobotCommand) {
        pendingCommand = command
    }
}
