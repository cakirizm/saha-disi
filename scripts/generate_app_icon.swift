import AppKit

let size = 1024
let canvas = NSImage(size: NSSize(width: size, height: size))
canvas.lockFocus()

NSColor(calibratedWhite: 0.97, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 0, y: 0, width: size, height: size)).fill()

let bubbleRect = NSRect(x: 150, y: 220, width: 724, height: 570)
let bubble = NSBezierPath(roundedRect: bubbleRect, xRadius: 120, yRadius: 120)
NSColor(calibratedWhite: 0.08, alpha: 1).setFill(); bubble.fill()

let tail = NSBezierPath(); tail.move(to: NSPoint(x: 260, y: 290)); tail.line(to: NSPoint(x: 205, y: 105)); tail.line(to: NSPoint(x: 430, y: 245)); tail.close(); tail.fill()

let field = NSRect(x: 215, y: 385, width: 594, height: 315)
NSColor.white.setStroke()
let outer = NSBezierPath(roundedRect: field, xRadius: 54, yRadius: 54); outer.lineWidth = 28; outer.stroke()

let mid = NSBezierPath(); mid.move(to: NSPoint(x: 512, y: 385)); mid.line(to: NSPoint(x: 512, y: 700)); mid.lineWidth = 24; mid.stroke()
let circle = NSBezierPath(ovalIn: NSRect(x: 432, y: 465, width: 160, height: 160)); circle.lineWidth = 24; circle.stroke()

for x in [215.0, 674.0] {
    let box = NSBezierPath(roundedRect: NSRect(x: x, y: 465, width: 135, height: 155), xRadius: 18, yRadius: 18)
    box.lineWidth = 24; box.stroke()
}

for x in [420.0, 512.0, 604.0] {
    let dot = NSBezierPath(ovalIn: NSRect(x: x - 18, y: 285, width: 36, height: 36)); dot.fill()
}

canvas.unlockFocus()
let tiff = canvas.tiffRepresentation!
let bitmap = NSBitmapImageRep(data: tiff)!
let png = bitmap.representation(using: .png, properties: [:])!
let path = "ios/SahaDisi/SahaDisi/Assets.xcassets/AppIcon.appiconset/AppIcon.png"
try png.write(to: URL(fileURLWithPath: path))
print("Generated Saha Dışı icon at \(path)")
