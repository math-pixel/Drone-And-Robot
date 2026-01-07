import SwiftUI

struct ContentView: View {

    @StateObject private var vm =
        PresentationSpheroActivityViewModel(
            wsURL: "ws://192.168.10.34:8057/ws"
        )

    var body: some View {
        VStack(spacing: 30) {

            Text("Presentation Sphero")
                .font(.largeTitle)
                .bold()

            if !vm.connected {
                Button("Connect To Server") {
                    vm.connect()
                }
                .font(.title)
                .padding()
                .frame(maxWidth: .infinity)
                .background(.blue)
                .foregroundColor(.white)
                .cornerRadius(16)
                .padding(.horizontal)
            }

            else if !vm.authorized {
                Text("⏳ Waiting for authorization…")
                    .font(.title2)
            }

            else if let robot = vm.robot {
                Toggle("Contrôle par inclinaison", isOn: $vm.useMotionControl)
                    .padding(.horizontal)
                
                if let robot = vm.robot {

                    if !vm.useMotionControl {
                        // 🎮 MODE JOYSTICK
                        JoystickView { x, y in
                            handleDirection(x: x, y: y, robot: robot)
                        }
                        .frame(width: 220, height: 220)

                    } else {
                        // 📱 MODE INCLINAISON
                        Text("📱 Incline le téléphone pour diriger")
                            .font(.headline)
                            .onAppear {
                                vm.startMotionControl { x, y in
                                    handleDirection(x: x, y: y, robot: robot)
                                }
                            }
                            .onDisappear {
                                vm.stopMotionControl()
                            }
                    }
                }

        
            }

            Spacer()
        }
        .padding()
    }

    // Même logique que ce que tu as déjà validé
    private func handleJoystick(x: CGFloat, y: CGFloat, robot: Robot) {
        let deadZone: CGFloat = 0.15

        if abs(x) < deadZone && abs(y) < deadZone {
            robot.stop()
            return
        }

        let angleRad = atan2(x, -y)
        var angleDeg = Int(angleRad * 180 / .pi)
        if angleDeg < 0 { angleDeg += 360 }

        robot.heading = angleDeg
        robot.forward(speed: 20) // lent
    }
    
    private func handleDirection(x: CGFloat, y: CGFloat, robot: Robot) {
        let deadZone: CGFloat = 0.15

        if abs(x) < deadZone && abs(y) < deadZone {
            robot.stop()
            return
        }

        // 🔄 gauche / droite inversés
        let angleRad = atan2(-x, -y)
        var angleDeg = Int(angleRad * 180 / .pi)
        if angleDeg < 0 { angleDeg += 360 }

        robot.heading = angleDeg
        robot.forward(speed: 40) // lent
    }

}


