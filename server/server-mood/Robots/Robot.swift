//
//  Robot.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//

import Foundation

/// Abstract base class for all your robots.
/// You never instantiate it directly.
/// You use Rover or Sphero, which inherit from it.
@Observable
class Robot {

    // MARK: - properties

    let bluetoothName: String
    private(set) var isConnected: Bool = false
    private(set) var lastSample: SensorSample = .empty
    var heading: Int = 0

    // MARK: - Simple callbacks

    var onConnect: (() -> Void)?
    var onDisconnect: (() -> Void)?
    var onSensorUpdate: ((SensorSample) -> Void)?


    // MARK: - Init

    init(bluetoothName: String) {
        self.bluetoothName = bluetoothName
    }

    // MARK: - "Abstract" methods to override

    func connect() {
        fatalError("connect() must be overridden in the subclass")
    }

    func disconnect() {
        fatalError("disconnect() must be overridden in the subclass")
    }

    func forward(speed: Int) {
        fatalError("forward() must be overridden in the subclass")
    }

    func backward(speed: Int) {
        fatalError("backward() must be overridden in the subclass")
    }

    func turn(degrees: Int) {
        fatalError("turn() must be overridden in the subclass")
    }

    func stop() {
        fatalError("stop() must be overridden in the subclass")
    }
}

// MARK: - Internal methods (for runners)

extension Robot {

    /// Called by the runner when Synchrosphere is ready.
    func _didConnect() {
        isConnected = true
        onConnect?()
    }

    /// Called by the runner when the controller is stopped.
    func _didDisconnect() {
        isConnected = false
        onDisconnect?()
    }

    /// Update sensors from Synchrosphere's `SyncsSample` type.
    func _updateFrom(syncsSample: SyncsSample) {
        let sample = SensorSample(
            x: syncsSample.x,
            y: syncsSample.y,
            vx: syncsSample.vx,
            vy: syncsSample.vy,
            ax: syncsSample.ax,
            ay: syncsSample.ay,
            yaw: syncsSample.yaw
        )
        lastSample = sample
        onSensorUpdate?(sample)
    }
}
