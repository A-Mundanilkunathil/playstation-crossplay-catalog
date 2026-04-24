import Foundation

/// Minimal GitHub Actions client — triggers the refresh workflow and polls
/// until a new run completes. Only the `workflow` PAT scope is required.
enum WorkflowDispatcher {
    static let owner = "A-Mundanilkunathil"
    static let repo = "playstation-crossplay-catalog"
    static let workflowFile = "refresh.yml"

    struct RunStatus: Decodable {
        let id: Int
        let status: String
        let conclusion: String?
        let runNumber: Int
        let createdAt: Date

        enum CodingKeys: String, CodingKey {
            case id, status, conclusion
            case runNumber = "run_number"
            case createdAt = "created_at"
        }
    }

    struct RunsResponse: Decodable {
        let workflowRuns: [RunStatus]
        enum CodingKeys: String, CodingKey { case workflowRuns = "workflow_runs" }
    }

    enum DispatchError: LocalizedError {
        case httpError(Int, String)
        case timedOut
        case cancelled
        case badResponse

        var errorDescription: String? {
            switch self {
            case .httpError(let code, let body): return "GitHub returned \(code): \(body)"
            case .timedOut: return "Rebuild didn't finish within 10 minutes."
            case .cancelled: return "Rebuild was cancelled."
            case .badResponse: return "Couldn't parse GitHub response."
            }
        }
    }

    static func dispatch(token: String) async throws {
        let url = URL(string: "https://api.github.com/repos/\(owner)/\(repo)/actions/workflows/\(workflowFile)/dispatches")!
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        req.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["ref": "main"])

        let (data, response) = try await URLSession.shared.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw DispatchError.badResponse }
        // 204 is success for workflow_dispatch.
        if http.statusCode != 204 {
            let body = String(data: data, encoding: .utf8) ?? ""
            throw DispatchError.httpError(http.statusCode, body)
        }
    }

    /// Poll /actions/runs until the latest workflow_dispatch run started AFTER
    /// `since` reaches status=completed. Calls `progress` each iteration.
    static func waitForCompletion(
        token: String,
        timeout: TimeInterval = 600,
        pollInterval: TimeInterval = 8,
        progress: @escaping (String) -> Void = { _ in }
    ) async throws {
        let start = Date()
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime]
        let dispatchMoment = start.addingTimeInterval(-15)

        while Date().timeIntervalSince(start) < timeout {
            try Task.checkCancellation()
            let run = try await latestDispatchRun(token: token)
            if let run, run.createdAt >= dispatchMoment {
                let detail = "Rebuilding… status: \(run.status)\(run.conclusion.map { " / \($0)" } ?? "")"
                progress(detail)
                if run.status == "completed" {
                    if run.conclusion == "success" { return }
                    throw DispatchError.httpError(0, "Workflow \(run.conclusion ?? "failed")")
                }
            } else {
                progress("Waiting for runner to pick up the job…")
            }
            try await Task.sleep(nanoseconds: UInt64(pollInterval * 1_000_000_000))
        }
        throw DispatchError.timedOut
    }

    private static func latestDispatchRun(token: String) async throws -> RunStatus? {
        var components = URLComponents(string: "https://api.github.com/repos/\(owner)/\(repo)/actions/runs")!
        components.queryItems = [
            URLQueryItem(name: "event", value: "workflow_dispatch"),
            URLQueryItem(name: "per_page", value: "1"),
        ]
        var req = URLRequest(url: components.url!)
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        req.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        req.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")

        let (data, _) = try await URLSession.shared.data(for: req)
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let runs = try decoder.decode(RunsResponse.self, from: data)
        return runs.workflowRuns.first
    }
}
