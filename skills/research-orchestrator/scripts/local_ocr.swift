#!/usr/bin/env swift

import AppKit
import CryptoKit
import Foundation
import Vision

struct OCRResult: Codable {
    let url: String
    let capturedAt: String
    let contentHash: String
    let normalizedHash: String
    let captureMethod: String
    let extractor: String
    let extractorVersion: String
    let status: String
    let publishedAtUnknownReason: String
    let locatorUnknownReason: String
    let extractionConfidence: String
    let engine: String
    let engineRevision: Int
    let mode: String
    let inputPath: String
    let inputBytes: Int
    let lines: Int
    let averageConfidence: Float
    let elapsedMilliseconds: Int
    let text: String

    enum CodingKeys: String, CodingKey {
        case url
        case capturedAt = "captured_at"
        case contentHash = "content_hash"
        case normalizedHash = "normalized_hash"
        case captureMethod = "capture_method"
        case extractor
        case extractorVersion = "extractor_version"
        case status
        case publishedAtUnknownReason = "published_at_unknown_reason"
        case locatorUnknownReason = "locator_unknown_reason"
        case extractionConfidence = "extraction_confidence"
        case engine
        case engineRevision
        case mode
        case inputPath
        case inputBytes
        case lines
        case averageConfidence
        case elapsedMilliseconds
        case text
    }
}

func sha256(_ data: Data) -> String {
    SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
}

guard CommandLine.arguments.count >= 2 else {
    FileHandle.standardError.write(Data("usage: local_ocr.swift IMAGE [--fast]\n".utf8))
    exit(2)
}

let inputPath = CommandLine.arguments[1]
let fast = CommandLine.arguments.contains("--fast")
let url = URL(fileURLWithPath: inputPath)
guard let image = NSImage(contentsOf: url) else {
    FileHandle.standardError.write(Data("error: could not load image\n".utf8))
    exit(2)
}

var rect = NSRect(origin: .zero, size: image.size)
guard let cgImage = image.cgImage(forProposedRect: &rect, context: nil, hints: nil) else {
    FileHandle.standardError.write(Data("error: could not convert image\n".utf8))
    exit(2)
}

let start = DispatchTime.now().uptimeNanoseconds
var observations: [VNRecognizedTextObservation] = []
var requestError: Error?
let request = VNRecognizeTextRequest { request, error in
    requestError = error
    observations = request.results as? [VNRecognizedTextObservation] ?? []
}
request.recognitionLevel = fast ? .fast : .accurate
request.usesLanguageCorrection = !fast

do {
    try VNImageRequestHandler(cgImage: cgImage, options: [:]).perform([request])
} catch {
    FileHandle.standardError.write(Data("error: \(error.localizedDescription)\n".utf8))
    exit(2)
}
if let error = requestError {
    FileHandle.standardError.write(Data("error: \(error.localizedDescription)\n".utf8))
    exit(2)
}

let candidates = observations.compactMap { $0.topCandidates(1).first }
let text = candidates.map(\.string).joined(separator: "\n")
let confidence = candidates.isEmpty ? 0 : candidates.map(\.confidence).reduce(0, +) / Float(candidates.count)
let elapsed = Int((DispatchTime.now().uptimeNanoseconds - start) / 1_000_000)
let bytes = (try? FileManager.default.attributesOfItem(atPath: inputPath)[.size] as? NSNumber)?.intValue ?? 0
let inputData = (try? Data(contentsOf: url)) ?? Data()
let outputData = Data(text.utf8)
let confidenceLabel = confidence >= 0.9 ? "high" : (confidence >= 0.7 ? "medium" : "low")
let result = OCRResult(
    url: url.standardizedFileURL.absoluteString,
    capturedAt: ISO8601DateFormatter().string(from: Date()),
    contentHash: "sha256:\(sha256(inputData))",
    normalizedHash: "sha256:\(sha256(outputData))",
    captureMethod: "local-ocr",
    extractor: "apple-vision",
    extractorVersion: String(VNRecognizeTextRequest.currentRevision),
    status: "captured",
    publishedAtUnknownReason: "local image has no publication metadata",
    locatorUnknownReason: "standalone image; add page or region when derived from a larger document",
    extractionConfidence: confidenceLabel,
    engine: "apple-vision",
    engineRevision: VNRecognizeTextRequest.currentRevision,
    mode: fast ? "fast" : "accurate",
    inputPath: url.standardizedFileURL.path,
    inputBytes: bytes,
    lines: candidates.count,
    averageConfidence: confidence,
    elapsedMilliseconds: elapsed,
    text: text
)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
let encoded = try encoder.encode(result)
FileHandle.standardOutput.write(encoded)
FileHandle.standardOutput.write(Data("\n".utf8))
