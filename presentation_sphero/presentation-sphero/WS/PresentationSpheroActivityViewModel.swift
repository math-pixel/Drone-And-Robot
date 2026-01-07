// PresentationSpheroActivityViewModel.swift
import Foundation
import Combine
import CoreMotion


@MainActor
final class PresentationSpheroActivityViewModel: ObservableObject {

    // UI state
    @Published var connected = false
    @Published var authorized = false

    // Robot
    @Published var robot: Robot?
    @Published var spheroID: String = "SB-808F"
    @Published var traveledDistance: Float = 0        // mètres (ou unité arbitraire)
    @Published var traveledProgress: Float = 0        // 0 → 1
    
    @Published var useMotionControl = false

    private let motionManager = CMMotionManager()

    @Published var steps: [Step] = [
        .init(
            id: 1,
            actions: [
                .init(id: 1, type: "video", file: "check_sensors.mp4", finished: false),
            ],
            authorized: false,
            finished: false
        )
    ]



    let clientKey = "presentation_sphero_activity"

    private let wsClient: PresentationSpheroActivityClient
    private var globalJSON: [String: Any] = [:]

    init(wsURL: String) {
        self.wsClient = PresentationSpheroActivityClient(wsURL: wsURL)
        self.wsClient.onMessage = handleMessage
    }

    // MARK: - Public

    func connect() {
        wsClient.connect()

    }

    // MARK: - Incoming WS

    private func handleMessage(_ json: [String: Any]) {
        globalJSON = json
        let key = json["key"] as? String ?? ""

        print("📥 Received:", key)

        switch key {

        case "identification_request":
            handleIdentification(json)

        case "presentation_sphero_activity_step_1_authorization":
            authorized = true
            connectToSphero()
            print("✅ Authorized → Sphero enabled")

        default:
            break
        }
    }

    // MARK: - Identification

    private func handleIdentification(_ json: [String: Any]) {
        var data = json
        data["key"] = "identification_\(clientKey)"

        if var activities = data["activity"] as? [[String: Any]] {
            for i in activities.indices {

                if var activity = activities[i][clientKey] as? [String: Any] {

                    activity["connected"] = true
                    activity["authorized"] = false
                    activity["finished"] = false

                    activity["steps"] = steps.map { step in
                        [
                            "id": step.id,
                            "actions": step.actions.map { action in
                                var a: [String: Any] = [
                                    "id": action.id,
                                    "type": action.type,
                                    "finished": false
                                ]
                                if let file = action.file { a["file"] = file }
                                if let chosen = action.chosen { a["chosen"] = chosen }
                                if let name = action.name { a["name"] = name }
                                if let options = action.options {
                                    a["options"] = options.map { ["id": $0.id, "text": $0.text] }
                                }
                                return a
                            },
                            "authorized": step.authorized,
                            "finished": false
                        ]
                    }

                    activities[i][clientKey] = activity
                }
            }

            data["activity"] = activities
        }

        wsClient.send(json: data)
        connected = true

        print("📤 identification_\(clientKey) sent with steps")
    }


    // MARK: - Robot

    func connectToSphero() {
        let robot = Sphero(bluetoothName: spheroID)
        self.robot = robot
        robot.connect()
    }
    
    func startMotionControl(onUpdate: @escaping (_ x: CGFloat, _ y: CGFloat) -> Void) {
        guard motionManager.isDeviceMotionAvailable else { return }

        motionManager.deviceMotionUpdateInterval = 1.0 / 30.0
        motionManager.startDeviceMotionUpdates(to: .main) { motion, _ in
            guard let motion else { return }

            // Inclinaison naturelle
            let roll = motion.attitude.roll      // gauche / droite
            let pitch = motion.attitude.pitch    // avant / arrière

            // Clamp entre -1 et 1
            let x = max(min(CGFloat(roll), 1), -1)
            let y = max(min(CGFloat(-pitch), 1), -1)

            onUpdate(x, y)
        }
    }

    func stopMotionControl() {
        motionManager.stopDeviceMotionUpdates()
    }

}
