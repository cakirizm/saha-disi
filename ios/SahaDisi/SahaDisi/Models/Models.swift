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

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        generatedAt = try values.decodeIfPresent(String.self, forKey: .generatedAt) ?? ""
        commentators = try values.decodeIfPresent([Commentator].self, forKey: .commentators) ?? []
        statements = try values.decodeIfPresent([Statement].self, forKey: .statements) ?? []
        matches = try values.decodeIfPresent([Match].self, forKey: .matches) ?? []
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

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        name = try values.decodeIfPresent(String.self, forKey: .name) ?? "Yorumcu"
        role = try values.decodeIfPresent(String.self, forKey: .role) ?? "Futbol yorumcusu"
        primarySource = try values.decodeIfPresent(String.self, forKey: .primarySource) ?? ""
        avatar = try values.decodeIfPresent(String.self, forKey: .avatar) ?? "?"
        photoURL = try values.decodeIfPresent(String.self, forKey: .photoURL)
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
    let imageURL: String?

    enum CodingKeys: String, CodingKey {
        case id, commentator, date, team, players, topic, type, sentiment, strength, summary, source, url, confidence, status
        case matchId = "match_id"
        case predictionOutcome = "prediction_outcome"
        case imageURL = "image_url"
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decodeIfPresent(Int.self, forKey: .id) ?? 0
        commentator = try values.decodeIfPresent(String.self, forKey: .commentator) ?? ""
        date = try values.decodeIfPresent(String.self, forKey: .date) ?? ""
        team = try values.decodeIfPresent(String.self, forKey: .team)
        players = try values.decodeIfPresent([String].self, forKey: .players) ?? []
        topic = try values.decodeIfPresent(String.self, forKey: .topic) ?? "Genel yorum"
        type = try values.decodeIfPresent(String.self, forKey: .type) ?? "opinion"
        sentiment = try values.decodeIfPresent(String.self, forKey: .sentiment) ?? "neutral"
        strength = try values.decodeIfPresent(Int.self, forKey: .strength) ?? 0
        summary = try values.decodeIfPresent(String.self, forKey: .summary) ?? ""
        source = try values.decodeIfPresent(String.self, forKey: .source) ?? ""
        url = try values.decodeIfPresent(String.self, forKey: .url) ?? ""
        confidence = try values.decodeIfPresent(Int.self, forKey: .confidence) ?? 0
        status = try values.decodeIfPresent(String.self, forKey: .status)
        matchId = try values.decodeIfPresent(String.self, forKey: .matchId)
        predictionOutcome = try values.decodeIfPresent(String.self, forKey: .predictionOutcome)
        imageURL = try values.decodeIfPresent(String.self, forKey: .imageURL)
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
    let homeLogoURL: String?
    let awayLogoURL: String?

    enum CodingKeys: String, CodingKey {
        case id, league, week, home, away, kickoff
        case homeScore = "home_score"
        case awayScore = "away_score"
        case imageURL = "image_url"
        case homeLogoURL = "home_logo_url"
        case awayLogoURL = "away_logo_url"
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        id = try values.decodeIfPresent(String.self, forKey: .id) ?? UUID().uuidString
        league = try values.decodeIfPresent(String.self, forKey: .league) ?? "Trendyol Süper Lig"
        week = try values.decodeIfPresent(Int.self, forKey: .week) ?? 0
        home = try values.decodeIfPresent(String.self, forKey: .home) ?? ""
        away = try values.decodeIfPresent(String.self, forKey: .away) ?? ""
        kickoff = try values.decodeIfPresent(String.self, forKey: .kickoff) ?? ""
        homeScore = try values.decodeIfPresent(Int.self, forKey: .homeScore)
        awayScore = try values.decodeIfPresent(Int.self, forKey: .awayScore)
        imageURL = try values.decodeIfPresent(String.self, forKey: .imageURL)
        homeLogoURL = try values.decodeIfPresent(String.self, forKey: .homeLogoURL)
        awayLogoURL = try values.decodeIfPresent(String.self, forKey: .awayLogoURL)
    }
}

struct RankedItem: Identifiable, Hashable {
    let id: String
    let name: String
    let count: Int
}
