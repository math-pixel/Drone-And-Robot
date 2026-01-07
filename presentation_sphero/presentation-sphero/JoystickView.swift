//
//  JoystickView.swift
//  presentation-sphero
//
//  Created by Thibaud Evrard on 18/12/2025.
//

import SwiftUI

struct JoystickView: View {

    let onMove: (_ x: CGFloat, _ y: CGFloat) -> Void

    @State private var offset: CGSize = .zero

    var body: some View {
        GeometryReader { geo in
            let radius = geo.size.width / 2
            let knobRadius: CGFloat = 40

            ZStack {
                Circle()
                    .fill(Color.gray.opacity(0.3))

                Circle()
                    .fill(Color.blue)
                    .frame(width: knobRadius * 2, height: knobRadius * 2)
                    .offset(offset)
                    .gesture(
                        DragGesture(minimumDistance: 0)
                            .onChanged { value in
                                let dx = value.translation.width
                                let dy = value.translation.height
                                let distance = sqrt(dx*dx + dy*dy)

                                if distance <= radius - knobRadius {
                                    offset = value.translation
                                } else {
                                    let angle = atan2(dy, dx)
                                    offset = CGSize(
                                        width: cos(angle) * (radius - knobRadius),
                                        height: sin(angle) * (radius - knobRadius)
                                    )
                                }

                                let normX = offset.width / (radius - knobRadius)
                                let normY = offset.height / (radius - knobRadius)
                                onMove(normX, normY)
                            }
                            .onEnded { _ in
                                offset = .zero
                                onMove(0, 0)
                            }
                    )
            }
        }
    }
}
