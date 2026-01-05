//
//  RobotCommand.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//


import Foundation

/// All commands that runners can send to the robot.
enum RobotCommand {
    case forward(speed: Int, durationS: Int = 1)
    case backward(speed: Int, durationS: Int = 1)
    case turn(heading: Int, durationS: Int = 1)
    case stop
    case rawWheels(left: Int, right: Int, durationS: Int = 1) 
}
