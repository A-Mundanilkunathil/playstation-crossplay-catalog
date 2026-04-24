import Foundation

struct Game: Codable, Identifiable, Hashable {
    let title: String
    let genres: [String]
    let tags: [String]
    let platforms: [String]
    let splitscreen: Bool?
    let onlineCoop: Bool?
    let players: Int?
    let rawgId: Int?
    let rawgSlug: String?
    let backgroundImage: String?
    let releaseYear: Int?
    let sources: [String]
    let confidence: String
    let crossplayPlatforms: [String]
    let inExtra: Bool
    let viewTypes: [String]

    var id: String { rawgSlug ?? title }

    enum CodingKeys: String, CodingKey {
        case title
        case genres
        case tags
        case platforms
        case splitscreen
        case onlineCoop = "online_coop"
        case players
        case rawgId = "rawg_id"
        case rawgSlug = "rawg_slug"
        case backgroundImage = "background_image"
        case releaseYear = "release_year"
        case sources
        case confidence
        case crossplayPlatforms = "crossplay_platforms"
        case inExtra = "in_extra"
        case viewTypes = "view_types"
    }

    func hasCombo(_ required: [String]) -> Bool {
        let set = Set(crossplayPlatforms)
        return required.allSatisfy { set.contains($0) }
    }
}
