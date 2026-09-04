import Foundation

struct FeedPayload: Codable {
    let generatedAt: String
    let commentators: [Commentator]
    let statements: [Statement]
    let matches: [Match]?

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case commentators, statements, matches
    }
}

struct Commentator: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let role: String
    let primarySource: String
    let avatar: String
    let photoURL: String?

    enum CodingKeys: String, CodingKey {
        case id, name, role, primarySource, avatar
        case photoURL = "photoURL"
    }
}

struct Statement: Codable, Identifiable, Hashable {
    let id: Int
    let commentator: String
    let date: String
    let team: String?
    let players: [String]
    let topic: String
    let type: String
    let sentiment: String
    let strength: Int
    let summary: String
    let source: String
    let url: String
    let confidence: Int
    let status: String?
    let matchId: String?
    let predictionOutcome: String?

    enum CodingKeys: String, CodingKey {
        case id, commentator, date, team, players, topic, type, sentiment, strength, summary, source, url, confidence, status
        case matchId = "match_id"
        case predictionOutcome = "prediction_outcome"
    }
}

struct Match: Codable, Identifiable, Hashable {
    let id: String
    let league: String
    let week: Int
    let home: String
    let away: String
    let kickoff: String
    let homeScore: Int?
    let awayScore: Int?
    let imageURL: String?

    enum CodingKeys: String, CodingKey {
        case id, league, week, home, away, kickoff
        case homeScore = "home_score"
        case awayScore = "away_score"
        case imageURL = "image_url"
    }
}

struct RankedItem: Identifiable, Hashable {
    let id: String
    let name: String
    let count: Int
}
