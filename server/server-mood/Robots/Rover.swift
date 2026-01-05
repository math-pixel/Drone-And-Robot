//
//  Rover.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//

import Foundation
import Pappe

/// Concrete implementation for Sphero RVR.
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

    override func forward(speed: Int) {
        runner?.send(.forward(speed: speed, durationS: 1))
    }

    override func backward(speed: Int) {
        runner?.send(.backward(speed: speed, durationS: 2))
    }

    /// Here we update the "logical" heading
    /// and let the runner interpret it as it sees fit.
    override func turn(degrees: Int) {
        heading = (heading + degrees) % 360
        if heading < 0 { heading += 360 }
        runner?.send(.turn(heading: heading, durationS: 1))
    }

    override func stop() {
        runner?.send(.stop)
    }
    
    func spinOneWheelLeft(durationS: Int = 1) {
        runner?.send(.rawWheels(left: 80, right: 0, durationS: durationS))
    }
    func spinOneWheelRight(durationS: Int = 1) {
        runner?.send(.rawWheels(left: 0, right: 80, durationS: durationS))
    }
    
    func spinLeftWheel(durationS: Int = 1) {
        // Simulation d’un pivot très lent sur la gauche
        runner?.send(.turn(heading: (heading - 10 + 360) % 360, durationS: durationS))
    }

    func spinRightWheel(durationS: Int = 1) {
        // Simulation d’un pivot très lent sur la droite
        runner?.send(.turn(heading: (heading + 10) % 360, durationS: durationS))
    }
}
