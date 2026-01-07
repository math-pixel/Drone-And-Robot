import Foundation

struct StepOption: Codable, Identifiable {
    let id: Int
    let text: String
}

struct StepAction: Codable, Identifiable {
    let id: Int
    let type: String

    var file: String?

    var chosen: Int?
    var name: String?
    var options: [StepOption]?

    var finished: Bool
}

struct Step: Codable, Identifiable {
    let id: Int
    var actions: [StepAction]
    var authorized: Bool
    var finished: Bool
}
