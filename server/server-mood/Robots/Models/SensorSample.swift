//
//  SensorSample.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//


import Foundation

/// Represents a sample of the robot's sensors, in a "clean" format.
struct SensorSample {
    let x: Float
    let y: Float
    let vx: Float
    let vy: Float
    let ax: Float
    let ay: Float
    let yaw: Float

    init(x: Float, y: Float, vx: Float, vy: Float, ax: Float, ay: Float, yaw: Float) {
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.ax = ax
        self.ay = ay
        self.yaw = yaw
    }

    static let empty = SensorSample(x: 0, y: 0, vx: 0, vy: 0, ax: 0, ay: 0, yaw: 0)
}
