import SwiftUI

struct ContentView: View {
    @EnvironmentObject var server: ServerManager
    @EnvironmentObject var rover: RoverControlManager

    private let cols = [
        GridItem(.flexible(minimum: 260), spacing: 12),
        GridItem(.flexible(minimum: 260), spacing: 12),
        GridItem(.flexible(minimum: 260), spacing: 12),
    ]

    var body: some View {
        VStack(spacing: 14) {
            
            HStack(alignment: .top, spacing: 12) {
                        RoverActivityPanel()
                            .frame(maxWidth: .infinity, alignment: .leading)

                        MomStepperControlPanel()
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

            // Top bar
            HStack(spacing: 12) {
                Button {
                    server.isRunning ? server.stop() : server.start()
                } label: {
                    Text(server.isRunning ? "Stop Server" : "Start Server")
                        .fontWeight(.semibold)
                        .frame(minWidth: 150)
                }
                .buttonStyle(.borderedProminent)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Local IP: \(server.localIPAddress ?? "—")")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)

                    Text("WS Server: \(server.wsServerAddress ?? "—")")
                        .font(.subheadline)
                        .monospaced()
                }

                Spacer()
                
                Button {
                    rover.toggleConnection()
                } label: {
                    Text(rover.isConnected ? "Disconnect Rover" : "Connect Rover")
                        .fontWeight(.semibold)
                        .frame(minWidth: 170)
                }
                .buttonStyle(.borderedProminent)

                Button {
                    server.startActivity()
                } label: {
                    Text(server.activityStarted ? "Activité en cours" : "Start Activity")
                        .fontWeight(.bold)
                        .frame(minWidth: 180)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(server.activityStarted || !server.canStartActivity)

                Button("Clear logs") { server.clearLogs() }
                    .buttonStyle(.bordered)
            }

            ScrollView {
                VStack(spacing: 14) {

                    

                    LazyVGrid(columns: cols, alignment: .leading, spacing: 12) {
                        ForEach(server.activityOrder, id: \.self) { name in
                            ActivityCard(
                                title: name,
                                sessionId: server.sessionIdByActivity[name] ?? "",
                                isConnected: server.activityConnected[name] ?? false,
                                isAuthorized: server.activityAuthorized[name] ?? false,
                                isFinished: server.activityFinished[name] ?? false,
                                actionSteps: server.activityActionSteps[name] ?? []
                            )
                        }
                    }
                    HStack(alignment: .top, spacing: 12) {
                        EmotionsPanel(items: server.emotions)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        LogsPanel(lines: server.logs)
                            .frame(maxWidth: .infinity, alignment: .leading)
                        
                        ///DebugJSONPanel(json: server.globalJSON)
                    }

                }
                .padding(.vertical, 4)
            }
        }
        .padding(16)
        .frame(minWidth: 860, minHeight: 640)
    }
}

// MARK: - Activity Card (split to help compiler)

private struct ActivityCard: View {
    @EnvironmentObject var server: ServerManager
    let title: String
    let sessionId: String
    let isConnected: Bool
    let isAuthorized: Bool
    let isFinished: Bool
    let actionSteps: [ActivityActionStep]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top, spacing: 12) {
                HeaderView(
                    title: title,
                    sessionId: sessionId,
                    isConnected: isConnected,
                    isAuthorized: isAuthorized,
                    isFinished: isFinished
                )
                Spacer()
            }

            CardContentView(
                activityName: title,
                isConnected: isConnected,
                actionSteps: actionSteps
            )
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(isConnected ? Color.green.opacity(0.22) : Color.gray.opacity(0.16))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(isConnected ? Color.green.opacity(0.35) : Color.gray.opacity(0.25), lineWidth: 1)
        )
    }
}

private struct HeaderView: View {
    let title: String
    let sessionId: String
    let isConnected: Bool
    let isAuthorized: Bool
    let isFinished: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                StatusDot(isConnected: isConnected, isAuthorized: isAuthorized, isFinished: isFinished)

                Text(title).font(.headline)

                if !sessionId.isEmpty {
                    Text(sessionId)
                        .font(.caption)
                        .monospaced()
                        .foregroundStyle(.secondary)
                }
            }

            Text(isConnected ? "Connected" : "Not connected")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

private struct CardContentView: View {
    @EnvironmentObject var server: ServerManager
    let activityName: String
    let isConnected: Bool
    let actionSteps: [ActivityActionStep]

    var body: some View {
        if actionSteps.isEmpty {
            Text("No steps")
                .font(.caption)
                .foregroundStyle(.secondary)
        } else {
            StepsOnlyView(activityName: activityName, isConnected: isConnected, steps: actionSteps)
        }
    }
}

private struct StepsOnlyView: View {
    @EnvironmentObject var server: ServerManager
    let activityName: String
    let isConnected: Bool
    let steps: [ActivityActionStep]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(steps) { s in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        StepAuthorizedDot(authorized: s.authorized, finished: s.finished)

                        Text("Step \(s.id)")
                            .font(.subheadline)
                            .fontWeight(.semibold)

                        Spacer()

                        if !s.authorized {
                            Button("Authorize") {
                                if activityName == "choice_activity" {
                                    server.authorizeChoiceStep(stepId: s.id)
                                } else {
                                    server.authorizeStep(activityName: activityName, stepId: s.id)
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .controlSize(.small)
                            .disabled(!isConnected)
                        }
                    }
                }
                .padding(10)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(Color.gray.opacity(0.10))
                )
            }
        }
        .padding(.top, 2)
    }
}

private struct StepsListView: View {
    let steps: [ActivityStep]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            ForEach(steps) { step in
                HStack(spacing: 10) {
                    Image(systemName: step.finished ? "checkmark.circle.fill" : "xmark.circle.fill")
                        .foregroundStyle(step.finished ? .green : .red)

                    Text("#\(step.id)")
                        .font(.caption)
                        .monospaced()
                        .foregroundStyle(.secondary)

                    Text(step.name)
                        .font(.subheadline)
                        .lineLimit(1)

                    Spacer(minLength: 0)
                }
            }
        }
        .padding(.top, 2)
    }
}

// MARK: - Choice Activity rendering (steps -> actions)

private struct ChoiceActivityView: View {
    let choiceSteps: [ChoiceStep]

    var body: some View {
        if choiceSteps.isEmpty {
            Text("No steps")
                .font(.caption)
                .foregroundStyle(.secondary)
        } else {
            VStack(alignment: .leading, spacing: 10) {
                ForEach(choiceSteps) { s in
                    ChoiceStepCard(step: s)
                }
            }
            .padding(.top, 2)
        }
    }
}
private struct ChoiceStepCard: View {
    @EnvironmentObject var server: ServerManager
    let step: ChoiceStep

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {

            HStack(spacing: 8) {
                StepAuthorizedDot(authorized: step.authorized, finished: step.finished)

                Text("Step \(step.id)")
                    .font(.subheadline)
                    .fontWeight(.semibold)

                Spacer()

                if !step.authorized {
                    Button("Authorize") {
                        server.authorizeChoiceStep(stepId: step.id)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(!(server.activityConnected["choice_activity"] ?? false))
                }
            }

            VStack(alignment: .leading, spacing: 6) {
                ForEach(step.actions) { a in
                    ChoiceActionRow(action: a) // ✅ no dot per action
                }
            }
            .padding(.leading, 2)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.gray.opacity(0.10))
        )
    }
}

private struct ChoiceActionRow: View {
    let action: ChoiceAction

    var body: some View {
        if action.type == "video" {
            HStack(spacing: 10) {
                Image(systemName: (action.finished ?? false) ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .foregroundStyle((action.finished ?? false) ? .green : .red)

                Text(action.file ?? "video")
                    .font(.caption)
                    .monospaced()
                    .foregroundStyle(.secondary)

                Spacer(minLength: 0)
            }

        } else if action.type == "choice" {
            VStack(alignment: .leading, spacing: 4) {
                Text(action.name ?? "choice")
                    .font(.subheadline)
                    .lineLimit(1)

                OptionsLine(options: action.options, chosen: action.chosen)
            }

        } else {
            HStack(spacing: 10) {
                Text("Unknown action")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer(minLength: 0)
            }
        }
    }
}

private struct OptionsLine: View {
    let options: [String]
    let chosen: Int

    private var chosenIndex: Int {
        if chosen == -1 { return -1 }
        if chosen == 0 || chosen == 1 { return chosen }      // ancien format
        if chosen >= 1 { return chosen - 1 }                 // nouveau format (id 1/2)
        return chosen
    }

    var body: some View {
        HStack(spacing: 10) {
            ForEach(options.indices, id: \.self) { idx in
                Text(options[idx])
                    .font(.caption)
                    .foregroundStyle(colorForOption(idx))
            }
            Spacer(minLength: 0)
        }
    }

    private func colorForOption(_ idx: Int) -> Color {
        if chosenIndex == -1 { return .secondary }
        return (chosenIndex == idx) ? .green : .red
    }
}

// MARK: - Emotions UI

private struct EmotionsPanel: View {
    let items: [EmotionItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Emotions").font(.headline)

            VStack(alignment: .leading, spacing: 10) {
                ForEach(items) { e in
                    EmotionGauge(type: e.type, value: e.level)
                }
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.gray.opacity(0.12))
        )
    }
}

private struct EmotionGauge: View {
    let type: String
    let value: Double // 0...37

    private var color: Color {
        switch type.lowercased() {
        case "happiness": return .green
        case "stress": return .blue
        case "shame": return .orange
        case "angry": return .red
        default: return .gray
        }
    }

    private let maxValue: Double = 37
    private var clamped: Double { min(maxValue, max(0, value)) }
    private var progress: Double { clamped / maxValue } // 0...1

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(type)
                    .font(.caption)
                    .fontWeight(.semibold)

                Spacer()

                Text(String(format: "%.1f", clamped))
                    .font(.caption)
                    .monospaced()
                    .foregroundStyle(.secondary)
            }

            GeometryReader { geo in
                let w = geo.size.width
                let fill = w * CGFloat(progress)

                ZStack(alignment: .leading) {
                    Capsule().fill(Color.gray.opacity(0.18))
                    Capsule().fill(color.opacity(0.85)).frame(width: fill)
                }
            }
            .frame(height: 10)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white.opacity(0.04))
        )
    }
}



// MARK: - Logs

private struct LogsPanel: View {
    let lines: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Logs").font(.headline)

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 6) {
                    ForEach(lines.indices, id: \.self) { i in
                        Text(lines[i])
                            .font(.caption)
                            .monospaced()
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.vertical, 6)
            }
            .frame(height: 220)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color.gray.opacity(0.12))
        )
    }
}


// MARK: - Status Dots

private struct StatusDot: View {
    let isConnected: Bool
    let isAuthorized: Bool
    let isFinished: Bool

    @State private var blink = false

    private var color: Color {
        if isFinished { return .green }
        if !isConnected { return .gray }
        if isConnected && !isAuthorized { return .red }
        return .blue
    }

    private var shouldBlink: Bool {
        isConnected && isAuthorized && !isFinished
    }

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 10, height: 10)
            .opacity(shouldBlink ? (blink ? 0.25 : 1.0) : 1.0)
            .onAppear { restartBlink() }
            .onChange(of: isConnected) { _, _ in restartBlink() }
            .onChange(of: isAuthorized) { _, _ in restartBlink() }
            .onChange(of: isFinished) { _, _ in restartBlink() }
    }

    private func restartBlink() {
        blink = false
        guard shouldBlink else { return }
        withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) {
            blink.toggle()
        }
    }
}

private struct StepAuthorizedDot: View {
    let authorized: Bool
    let finished: Bool

    @State private var pulse = false

    private var shouldBlink: Bool { authorized && !finished }

    private var color: Color {
        if finished { return .green }
        return authorized ? .blue : .red
    }

    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 9, height: 9)
            .opacity(shouldBlink ? (pulse ? 0.25 : 1.0) : 1.0)
            .onAppear { restart() }
            .onChange(of: authorized) { _, _ in restart() }
            .onChange(of: finished) { _, _ in restart() }
    }

    private func restart() {
        pulse = false
        guard shouldBlink else { return }
        withAnimation(.easeInOut(duration: 0.6).repeatForever(autoreverses: true)) {
            pulse.toggle()
        }
    }
}


struct RoverActivityPanel: View {
    @EnvironmentObject var rover: RoverControlManager

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("throw_rover_actitvity")
                    .font(.headline)

                Spacer()

                Button {
                    rover.toggleConnection()
                } label: {
                    Text(rover.isConnected ? "Disconnect Rover" : "Connect Rover")
                        .fontWeight(.semibold)
                        .frame(minWidth: 170)
                }
                .buttonStyle(.borderedProminent)
            }

            Text(rover.isConnected ? "Connected" : "Not connected")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                Button("Left")  { rover.left() }
                Button("Forward") { rover.forward() }
                Button("Right") { rover.right() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!rover.isConnected)

            HStack(spacing: 10) {
                Button("Backward") { rover.backward() }
                Button("Stop") { rover.stop() }
            }
            .buttonStyle(.bordered)
            .disabled(!rover.isConnected)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.gray.opacity(0.12))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color.gray.opacity(0.25), lineWidth: 1)
        )
    }
}



// ✅ Nouveau rendu générique "steps -> actions" pour TOUTES les activities

private struct ActionStepsView: View {
    let activityName: String
    let isConnected: Bool
    let steps: [ActivityActionStep]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(steps) { s in
                ActionStepCard(activityName: activityName, isConnected: isConnected, step: s)
            }
        }
        .padding(.top, 2)
    }
}

private struct ActionStepCard: View {
    @EnvironmentObject var server: ServerManager
    let activityName: String
    let isConnected: Bool
    let step: ActivityActionStep

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                StepAuthorizedDot(authorized: step.authorized, finished: step.finished)

                Text("Step \(step.id)")
                    .font(.subheadline)
                    .fontWeight(.semibold)

                Spacer()

                if !step.authorized {
                    Button("Authorize") {
                        server.authorizeStep(activityName: activityName, stepId: step.id)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(!isConnected)
                }
            }

            VStack(alignment: .leading, spacing: 8) {
                ForEach(step.actions) { a in
                    ActionRow(stepAuthorized: step.authorized, action: a)
                }
            }
            .padding(.leading, 2)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.gray.opacity(0.10))
        )
    }
}

private struct ActionRow: View {
    let stepAuthorized: Bool
    let action: ActivityAction

    private var isDone: Bool {
        if action.type == "choice" {
            return (action.finished ?? false) || (action.chosen ?? -1) != -1
        }
        return (action.finished ?? false)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 10) {
                StepAuthorizedDot(authorized: stepAuthorized, finished: isDone)

                if action.type == "video" {
                    Text(action.file ?? "video")
                        .font(.caption)
                        .monospaced()
                        .foregroundStyle(.secondary)
                } else if action.type == "choice" {
                    Text(action.name ?? "choice")
                        .font(.subheadline)
                        .lineLimit(1)
                } else {
                    Text("Unknown action")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer(minLength: 0)
            }

            if action.type == "choice" {
                OptionsLine(options: action.options ?? [], chosen: action.chosen ?? -1)
                    .padding(.leading, 19) // aligne avec le texte après le dot
            }
        }
    }
}
private struct DebugJSONPanel: View {
    let json: [String: Any]
    @State private var expanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Debug JSON").font(.headline)
                Spacer()
                Button(expanded ? "Hide" : "Show") { expanded.toggle() }
                    .buttonStyle(.bordered)
            }

            if expanded {
                ScrollView {
                    Text(pretty(json) ?? "—")
                        .font(.caption)
                        .monospaced()
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(10)
                        .background(Color.gray.opacity(0.08))
                        .cornerRadius(10)
                }
                .frame(height: 260)
            }
        }
        .padding(12)
        .background(RoundedRectangle(cornerRadius: 14).fill(Color.gray.opacity(0.12)))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.gray.opacity(0.25), lineWidth: 1))
    }

    private func pretty(_ json: [String: Any]) -> String? {
        guard let data = try? JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted, .sortedKeys]),
              let s = String(data: data, encoding: .utf8)
        else { return nil }
        return s
    }
}

// ✅ ADD this new panel (same file as RoverActivityPanel is fine)

struct MomStepperControlPanel: View {
    @EnvironmentObject var server: ServerManager

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("mom_stepper_control")
                .font(.headline)

            Text((server.activityConnected["mom_stepper_activity"] ?? false) ? "mom_stepper_activity connected" : "mom_stepper_activity not connected")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            HStack(spacing: 10) {
                Button("Init position") {
                    server.sendKey("mom_activity_stepper_control_init_position", to: "mom_stepper_activity")
                }
                .buttonStyle(.borderedProminent)
                .disabled(!(server.activityConnected["mom_stepper_activity"] ?? false))
            }

            HStack(spacing: 10) {
                Button("Left") {
                    server.sendKey("mom_activity_stepper_control_turn_left_5", to: "mom_stepper_activity")
                }
                Button("Right") {
                    server.sendKey("mom_activity_stepper_control_turn_right_5", to: "mom_stepper_activity")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(!(server.activityConnected["mom_stepper_activity"] ?? false))
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .fill(Color.gray.opacity(0.12))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(Color.gray.opacity(0.25), lineWidth: 1)
        )
    }
}
