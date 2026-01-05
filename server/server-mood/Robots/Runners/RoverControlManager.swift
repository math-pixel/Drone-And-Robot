//
//  RoverControlManager.swift
//  server-mood
//
//  Created by Thibaud Evrard on 19/12/2025.
//

// RoverControlManager.swift — NEW (simple, fixed name RV-4531, no LEDs, no sensors, no lever)
import Foundation
import Combine

@MainActor
final class RoverControlManager: ObservableObject {
    @Published private(set) var isConnected: Bool = false

    private let bluetoothName: String = "RV-4531"
    private var rover: Rover?

    private var pollTask: Task<Void, Never>?

    func toggleConnection() {
        if let rover, rover.isConnected {
            rover.disconnect()
            self.rover = nil
            isConnected = false
            stopPolling()
        } else {
            let r = Rover(bluetoothName: bluetoothName)
            rover = r
            r.connect()
            startPolling()
        }
    }
    
    func spinWheelLeft()  { rover?.spinOneWheelLeft(durationS: 1) }
    func spinWheelRight() { rover?.spinOneWheelRight(durationS: 1) }
    
    func spinLeftWheel() {
        rover?.spinLeftWheel(durationS: 1)
    }

    func spinRightWheel() {
        rover?.spinRightWheel(durationS: 1)
    }

    func forward()  { rover?.forward(speed: 100) }
    func backward() { rover?.backward(speed: 80) }
    func left()     { rover?.turn(degrees: -15) }
    func right()    { rover?.turn(degrees: 15) }
    func stop()     { rover?.stop() }

    private func startPolling() {
        stopPolling()
        pollTask = Task { [weak self] in
            while !Task.isCancelled {
                await MainActor.run {
                    self?.isConnected = self?.rover?.isConnected ?? false
                }
                try? await Task.sleep(nanoseconds: 200_000_000)
            }
        }
    }

    private func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }
}
