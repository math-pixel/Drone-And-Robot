import SwiftUI

@main
struct server_moodApp: App {
    @StateObject private var server = ServerManager()
    @StateObject private var rover = RoverControlManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(server)
                .environmentObject(rover)          
        }
    }
}
