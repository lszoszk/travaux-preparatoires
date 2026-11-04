// Apple Vision OCR for page images. Local and free (macOS Vision framework).
//
// Build:  swiftc -O pipeline/vision_ocr.swift -o bin/vision_ocr
// Usage:  bin/vision_ocr [--no-lc] page-001.png page-002.png ...
//         --no-lc turns off Vision's language correction, which can "correct" typewriter
//         misreadings into wrong dictionary words.
// Output: one JSON object per image on stdout:
//   {"image": path, "lines": [{"text", "conf", "x", "y", "w", "h"}, ...]}
// Coordinates are normalised to 0..1 with the origin at the top left.
import AppKit
import Foundation
import Vision

var paths = Array(CommandLine.arguments.dropFirst())
let languageCorrection = !paths.contains("--no-lc")
paths.removeAll { $0 == "--no-lc" }

for path in paths {
    guard let image = NSImage(contentsOfFile: path),
          let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("cannot read \(path)\n".data(using: .utf8)!)
        continue
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = languageCorrection
    request.recognitionLanguages = ["en-US"]
    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([request])
    } catch {
        FileHandle.standardError.write("vision failed on \(path): \(error)\n".data(using: .utf8)!)
        continue
    }
    var lines: [[String: Any]] = []
    for observation in request.results ?? [] {
        guard let best = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        lines.append([
            "text": best.string,
            "conf": Double(best.confidence),
            "x": Double(box.origin.x),
            "y": Double(1 - box.origin.y - box.height),
            "w": Double(box.width),
            "h": Double(box.height),
        ])
    }
    let data = try! JSONSerialization.data(withJSONObject: ["image": path, "lines": lines])
    print(String(data: data, encoding: .utf8)!)
}
