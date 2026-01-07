// ContentView.swift
import SwiftUI

struct ContentView: View {

    @StateObject private var vm =
        PresentationSpheroActivityViewModel(
            wsURL: "ws://192.168.1.13:8057/ws"
        )

    var body: some View {
        VStack(spacing: 22) {

            Text("Presentation Sphero")
                .font(.largeTitle)
                .bold()

            // ✅ SETUP SCREEN (Server + Calibration)
            let setupReady = vm.connected && vm.isCalibrated && vm.robot != nil

            if !setupReady {

                // 1) SERVER
                VStack(alignment: .leading, spacing: 12) {
                    Text("🌐 Serveur")
                        .font(.title3)
                        .bold()

                    if vm.connected {
                        Text("✅ Connecté au serveur")
                            .font(.headline)
                    } else {
                        Button("Connect To Server") {
                            vm.connect()
                        }
                        .font(.title3)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(.blue)
                        .foregroundColor(.white)
                        .cornerRadius(16)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(.gray.opacity(0.12))
                .cornerRadius(18)
                .padding(.horizontal)

                // 2) CALIBRATION
                VStack(alignment: .leading, spacing: 12) {
                    Text("🧭 Calibration Sphero")
                        .font(.title3)
                        .bold()

                    if vm.robot == nil {
                        Text("Connecte le Sphero pour pouvoir le calibrer.")
                            .foregroundStyle(.secondary)

                        Button("Connect Sphero") {
                            vm.connectToSphero()
                        }
                        .font(.title3)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(.purple)
                        .foregroundColor(.white)
                        .cornerRadius(16)

                    } else if !vm.isCalibrated {

                        Text("Fais tourner le Sphero pour aligner l’avant avec la vraie vie.")
                            .foregroundStyle(.secondary)

                        Text("Offset: \(vm.headingOffset)°")
                            .font(.headline)
                            .monospaced()

                        HStack(spacing: 14) {
                            Button("↺ Gauche") { vm.calibrationTurn(-10) }
                                .font(.title2)
                                .padding(.vertical, 12)
                                .frame(maxWidth: .infinity)
                                .background(.gray.opacity(0.2))
                                .cornerRadius(14)

                            Button("↻ Droite") { vm.calibrationTurn(10) }
                                .font(.title2)
                                .padding(.vertical, 12)
                                .frame(maxWidth: .infinity)
                                .background(.gray.opacity(0.2))
                                .cornerRadius(14)
                        }

                        HStack(spacing: 14) {
                            Button("↺ Fin") { vm.calibrationTurn(-1) }
                                .padding(.vertical, 10)
                                .frame(maxWidth: .infinity)
                                .background(.gray.opacity(0.12))
                                .cornerRadius(14)

                            Button("↻ Fin") { vm.calibrationTurn(1) }
                                .padding(.vertical, 10)
                                .frame(maxWidth: .infinity)
                                .background(.gray.opacity(0.12))
                                .cornerRadius(14)
                        }

                        Button("OK, c’est calibré") {
                            vm.confirmCalibration()
                        }
                        .font(.title3)
                        .padding()
                        .frame(maxWidth: .infinity)
                        .background(.green)
                        .foregroundColor(.white)
                        .cornerRadius(16)

                    } else {
                        Text("✅ Calibré")
                            .font(.headline)
                    }
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(.gray.opacity(0.12))
                .cornerRadius(18)
                .padding(.horizontal)

                if vm.connected && vm.isCalibrated {
                    Text("⏳ En attente du début de l’activité…\nLe téléphone peut être placé dans la boîte.")
                        .multilineTextAlignment(.center)
                        .font(.title3)
                        .padding(.horizontal)
                }

            }

            // ✅ WAIT AUTH (phone can be put in the box)
            else if !vm.authorized {
                Text("⏳ En attente du début de l’activité…\nLe téléphone peut être placé dans la boîte.")
                    .multilineTextAlignment(.center)
                    .font(.title3)
                    .padding(.horizontal)
            }

            // ✅ CONTROL (only after authorized)
            else if let robot = vm.robot {

                Toggle("Contrôle par inclinaison", isOn: $vm.useMotionControl)
                    .padding(.horizontal)

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

            Spacer()
        }
        .padding()
    }

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
        robot.forward(speed: 20)
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

        let calibrated = (angleDeg + vm.headingOffset) % 360
        robot.heading = calibrated
        robot.forward(speed: 40)
    }
}
