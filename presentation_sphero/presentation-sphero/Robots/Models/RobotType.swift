//
//  RobotType.swift
//  IOTTools
//
//  Created by Emmanuel Moulin on 29/11/2025.
//

import Foundation

enum RobotType {
    case rover
    case sphero
    
    func toSynchroSphere() -> SyncsDeviceSelector {
        return switch (self) {
            case .rover:
                .anyRVR
            case .sphero:
                .anyBolt
        }
    }
}
