//
//  BatteryState.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//


import Foundation

/// Simplified status of the robot's battery.
enum BatteryState {
    case ok
    case low
    case critical
    case unknown
}
