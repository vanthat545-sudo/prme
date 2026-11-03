import AppKit
import Foundation

func fillRounded(_ rect: NSRect, _ radius: CGFloat, _ color: NSColor) {
    color.setFill()
    NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius).fill()
}
func fillCircle(_ rect: NSRect, _ color: NSColor) {
    color.setFill()
    NSBezierPath(ovalIn: rect).fill()
}
func line(_ points: [NSPoint], width: CGFloat, color: NSColor) {
    guard let first = points.first else { return }
    let path = NSBezierPath()
    path.move(to: first)
    for pt in points.dropFirst() { path.line(to: pt) }
    path.lineWidth = width
    path.lineCapStyle = .round
    path.lineJoinStyle = .round
    color.setStroke()
    path.stroke()
}
let size = 1024
let image = NSImage(size: NSSize(width: size, height: size), flipped: false) { _ in
    let background = NSRect(x: 14, y: 14, width: 996, height: 996)
    let backgroundPath = NSBezierPath(roundedRect: background, xRadius: 220, yRadius: 220)
    let gradient = NSGradient(starting: NSColor(calibratedRed: 0.10, green: 0.66, blue: 1, alpha: 1),
                              ending: NSColor(calibratedRed: 0.01, green: 0.16, blue: 0.55, alpha: 1))!
    gradient.draw(in: backgroundPath, angle: -70)
    fillRounded(NSRect(x: 435, y: 300, width: 430, height: 445), 48, .white)
    fillRounded(NSRect(x: 435, y: 635, width: 430, height: 110), 46,
                NSColor(calibratedRed: 0.07, green: 0.44, blue: 0.93, alpha: 1))
    for x in [545.0, 755.0] {
        fillRounded(NSRect(x: x, y: 705, width: 43, height: 100), 19, .white)
    }
    let light = NSColor(calibratedRed: 0.75, green: 0.82, blue: 0.93, alpha: 1)
    for x in [510.0, 600.0, 690.0, 780.0] {
        for y in [380.0, 470.0, 560.0] {
            fillRounded(NSRect(x: x, y: y, width: 55, height: 55), 12, light)
        }
    }
    fillRounded(NSRect(x: 690, y: 470, width: 55, height: 55), 12, .systemBlue)
    line([NSPoint(x: 702, y: 493), NSPoint(x: 713, y: 482), NSPoint(x: 736, y: 513)], width: 9, color: .white)
    fillCircle(NSRect(x: 130, y: 350, width: 515, height: 515), NSColor(calibratedRed: 0.10, green: 0.51, blue: 0.98, alpha: 1))
    fillCircle(NSRect(x: 162, y: 382, width: 451, height: 451), .white)
    let center = NSPoint(x: 387.5, y: 607.5)
    for index in 0..<12 {
        let angle = Double(index) * Double.pi / 6
        let outer = CGFloat(197.0)
        let inner = CGFloat(index % 3 == 0 ? 175.0 : 185.0)
        let p1 = NSPoint(x: center.x + outer * CGFloat(sin(angle)), y: center.y + outer * CGFloat(cos(angle)))
        let p2 = NSPoint(x: center.x + inner * CGFloat(sin(angle)), y: center.y + inner * CGFloat(cos(angle)))
        line([p1, p2], width: index % 3 == 0 ? 12 : 7,
             color: NSColor(calibratedRed: 0.12, green: 0.22, blue: 0.41, alpha: 1))
    }
    let navy = NSColor(calibratedRed: 0.10, green: 0.20, blue: 0.37, alpha: 1)
    line([center, NSPoint(x: 299, y: 672)], width: 22, color: navy)
    line([center, NSPoint(x: 499, y: 706)], width: 22, color: navy)
    fillCircle(NSRect(x: 365, y: 585, width: 45, height: 45), .systemBlue)
    fillCircle(NSRect(x: 590, y: 275, width: 195, height: 195), NSColor(calibratedRed: 0.04, green: 0.73, blue: 0.44, alpha: 1))
    line([NSPoint(x: 631, y: 371), NSPoint(x: 672, y: 333), NSPoint(x: 749, y: 410)], width: 26, color: .white)
    let label = "Chấm Công Mac" as NSString
    let attrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: 81, weight: .bold),
        .foregroundColor: NSColor.white
    ]
    let labelSize = label.size(withAttributes: attrs)
    label.draw(at: NSPoint(x: (CGFloat(size) - labelSize.width) / 2, y: 133), withAttributes: attrs)
    return true
}
let rep = NSBitmapImageRep(data: image.tiffRepresentation!)!
let data = rep.representation(using: .png, properties: [:])!
let destination = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "AppIcon.png"
try data.write(to: URL(fileURLWithPath: destination))
print("Wrote \(destination)")
