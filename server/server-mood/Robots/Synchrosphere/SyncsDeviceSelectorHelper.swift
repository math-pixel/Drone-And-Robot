// Project Synchrosphere
// Copyright 2021, Framework Labs.

/// NOTE:
/// `isRVR` must be accessible from other files (ex: SpheroController),
/// so keep this extension at *internal* level (no `private` / `fileprivate`).

extension SyncsDeviceSelector {
    var isRVR: Bool {
        switch self {
        case .anyRVR:
            return true
        case .anyMini, .anyBolt, .named:
            return false
        }
    }

    var needsTheForce: Bool {
        switch self {
        case .anyRVR:
            return false
        case .anyMini, .anyBolt:
            return true
        case .named:
            // Mini/Bolt need the force, RVR doesn't.
            // For a specific name, it depends on the device.
            // If you only use `.named` for Mini/Bolt, keep `true`.
            // Otherwise, you can adapt later (e.g. based on prefix).
            return true
        }
    }

    var namePrefix: String? {
        switch self {
        case .anyRVR:  return "RV-"
        case .anyMini: return "SM-"
        case .anyBolt: return "SB-"
        case .named:   return nil
        }
    }
}
