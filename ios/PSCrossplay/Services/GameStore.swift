import Foundation
import SwiftUI

@MainActor
final class GameStore: ObservableObject {
    enum LoadState: Equatable {
        case idle
        case loading
        case rebuilding(message: String)
        case error(String)
    }

    static let gamesURL = URL(
        string: "https://a-mundanilkunathil.github.io/playstation-crossplay-catalog/games.json"
    )!

    @Published private(set) var games: [Game] = []
    @Published private(set) var lastUpdated: Date?
    @Published var state: LoadState = .idle

    private let cacheFileURL: URL
    private let seedResource = "seed-games"

    init() {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.cacheFileURL = dir.appendingPathComponent("games.cache.json")
        loadFromDiskOrSeed()
    }

    func loadFromDiskOrSeed() {
        if let data = try? Data(contentsOf: cacheFileURL),
           let decoded = try? JSONDecoder().decode([Game].self, from: data) {
            self.games = decoded
            return
        }
        if let url = Bundle.main.url(forResource: seedResource, withExtension: "json"),
           let data = try? Data(contentsOf: url),
           let decoded = try? JSONDecoder().decode([Game].self, from: data) {
            self.games = decoded
        }
    }

    /// Fast refresh: re-fetch the pre-built games.json from GitHub Pages.
    func reloadFromServer() async {
        state = .loading
        do {
            var req = URLRequest(url: Self.gamesURL)
            req.cachePolicy = .reloadIgnoringLocalCacheData
            let (data, response) = try await URLSession.shared.data(for: req)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                throw URLError(.badServerResponse)
            }
            let decoded = try JSONDecoder().decode([Game].self, from: data)
            self.games = decoded
            self.lastUpdated = Date()
            try? data.write(to: cacheFileURL)
            state = .idle
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    /// Slow refresh: kick GitHub Actions, wait for the workflow to finish, then
    /// call `reloadFromServer`. Requires a PAT with `workflow` scope in Keychain.
    func rebuildThenReload() async {
        guard let token = KeychainPAT.load() else {
            state = .error("Add a GitHub token in Settings to rebuild.")
            return
        }
        state = .rebuilding(message: "Starting rebuild…")
        do {
            try await WorkflowDispatcher.dispatch(token: token)
            state = .rebuilding(message: "Rebuilding… (~2 min)")
            try await WorkflowDispatcher.waitForCompletion(token: token) { status in
                Task { @MainActor in
                    self.state = .rebuilding(message: status)
                }
            }
            await reloadFromServer()
        } catch {
            state = .error(error.localizedDescription)
        }
    }

    var extraPS4PS5: [Game] { games.filter { $0.inExtra && $0.hasCombo(["PS4", "PS5"]) } }
    var extraPS5PC: [Game] { games.filter { $0.inExtra && $0.hasCombo(["PS5", "PC"]) } }
    var extraAll: [Game] { games.filter { $0.inExtra && $0.hasCombo(["PS4", "PS5", "PC"]) } }
    var allPS5PC: [Game] { games.filter { $0.hasCombo(["PS5", "PC"]) } }
    var allTriple: [Game] { games.filter { $0.hasCombo(["PS4", "PS5", "PC"]) } }
}
