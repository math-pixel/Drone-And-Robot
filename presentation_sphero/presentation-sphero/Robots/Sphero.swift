//
//  Sphero.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//

import Foundation

/// Concrete implementation for Sphero Mini.
final class Sphero: Robot {
    
    internal var runner: SpheroRunner?

    override init(bluetoothName: String) {
        super.init(bluetoothName: bluetoothName)
        self.runner = SpheroRunner(robot: self)
    }

    override func connect() {
        runner?.connect()
    }

    override func disconnect() {
        runner?.disconnect()
    }

    override func forward(speed: Int) {
        runner?.send(.forward(speed: speed))
    }

    override func backward(speed: Int) {
        runner?.send(.backward(speed: speed))
    }

    override func turn(degrees: Int) {
        heading = (heading + degrees) % 360
        if heading < 0 { heading += 360 }
        runner?.send(.turn(heading: heading))
    }

    override func stop() {
        runner?.send(.stop)
    }

}
