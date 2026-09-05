import Foundation

struct FeedPayload: Codable {
    let generatedAt: String
    let commentators: [Commentator]
    let statements: [Statement]
    let matches: [Match]?
    let players: [PlayerProfile]?

    enum CodingKeys: String, CodingKey {
        case generatedAt = "generated_at"
        case commentators, statements, matches, players
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        generatedAt = try values.decodeIfPresent(String.self, forKey: .generatedAt) ?? ""
        commentators = try values.decodeIfPresent([Commentator].self, forKey: .commentators) ?? []
        statements = try values.decodeIfPresent([Statement].self, forKey: .statements) ?? []
        matches = try values.decodeIfPresent([Match].self, forKey: .matches) ?? []
        players = try values.decodeIfPresent([PlayerProfile].self, forKey: .players) ?? []
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
        imageURL = nil // Commentary artwork comes from the verified commentator identity.
    }
}

extension Statement {
    /// Kaynak bir video mu yoksa yazılı haber mi? Yönlendirme metnini buna göre seçiyoruz.
    var isVideoSource: Bool {
        let u = url.lowercased()
        return u.contains("youtube.com") || u.contains("youtu.be")
    }
    /// "Tamamını izlemek/okumak isteyeni oraya yönlendir" — eyleme dönük başlık.
    var sourceActionTitle: String {
        let host = URL(string: url)?.host?.lowercased() ?? ""
        if ["x.com", "twitter.com", "instagram.com", "www.instagram.com", "www.x.com"].contains(host) { return "Paylaşımı aç" }
        return isVideoSource ? "Videoyu izle" : "Habere git"
    }
    var sourceActionIcon: String { isVideoSource ? "play.rectangle.fill" : "arrow.up.right" }
    var sourceActionHint: String {
        isVideoSource ? "Tamamını izlemek için \(source) kaynağına git"
                      : "Tamamını okumak için \(source) kaynağına git"
    }
}

/// A cluster of statements where several commentators share the same stance
/// (same topic + team + sentiment). Deduped to one statement per commentator.
struct StatementGroup: Identifiable, Hashable {
    let id: String
    let topic: String
    let team: String?
    let sentiment: String
    let statements: [Statement]

    var lead: Statement { statements[0] }
    var commentatorCount: Int { Set(statements.map(\.commentator)).count }
    var isCluster: Bool { statements.count >= 2 }
    var date: String { statements.map(\.date).max() ?? "" }
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
    let status: String?
    let venue: String?
    let referee: String?
    let attendance: Int?
    let statistics: [MatchStatistic]
    let events: [MatchEvent]
    let playerRatings: [PlayerMatchRating]

    enum CodingKeys: String, CodingKey {
        case id, league, week, home, away, kickoff
        case homeScore = "home_score"
        case awayScore = "away_score"
        case imageURL = "image_url"
        case homeLogoURL = "home_logo_url"
        case awayLogoURL = "away_logo_url"
        case status, venue, referee, attendance, statistics, events
        case playerRatings = "player_ratings"
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
        status = try values.decodeIfPresent(String.self, forKey: .status)
        venue = try values.decodeIfPresent(String.self, forKey: .venue)
        referee = try values.decodeIfPresent(String.self, forKey: .referee)
        attendance = try values.decodeIfPresent(Int.self, forKey: .attendance)
        statistics = try values.decodeIfPresent([MatchStatistic].self, forKey: .statistics) ?? []
        events = try values.decodeIfPresent([MatchEvent].self, forKey: .events) ?? []
        playerRatings = try values.decodeIfPresent([PlayerMatchRating].self, forKey: .playerRatings) ?? []
    }
}

extension Match {
    var scoreText: String {
        if let homeScore, let awayScore { return "\(homeScore) - \(awayScore)" }
        return statusText == "Başlamadı" ? "VS" : "—"
    }

    var statusText: String {
        switch status {
        case "live": return "Canlı"
        case "finished": return "Maç bitti"
        case "postponed": return "Ertelendi"
        case "cancelled": return "İptal edildi"
        case "suspended": return "Durduruldu"
        default: break
        }
        if homeScore != nil && awayScore != nil { return "Maç bitti" }
        var date = ISO8601DateFormatter().date(from: kickoff)
        if date == nil {
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "tr_TR")
            formatter.timeZone = TimeZone(identifier: "Europe/Istanbul")
            formatter.dateFormat = "dd.MM.yyyy HH:mm"
            date = formatter.date(from: kickoff)
        }
        guard let date else { return "Tarih bekleniyor" }
        return date <= Date() ? "Sonuç bekleniyor" : "Başlamadı"
    }
}

struct MatchStatistic: Codable, Hashable {
    let name: String
    let home: String
    let away: String
}

struct MatchEvent: Codable, Identifiable, Hashable {
    let id: String
    let minute: Int
    let type: String
    let team: String
    let player: String?
    let detail: String?
}

struct PlayerMatchRating: Codable, Identifiable, Hashable {
    var id: String { "\(team)-\(player)" }
    let player: String
    let team: String
    let rating: Double?
    let minutes: Int?
    let goals: Int?
    let assists: Int?
}

struct PlayerProfile: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let team: String?
    let position: String?
    let number: Int?
    let photoURL: String?
    let appearances: Int?
    let minutes: Int?
    let goals: Int?
    let assists: Int?
    let yellowCards: Int?
    let redCards: Int?
    let averageRating: Double?

    enum CodingKeys: String, CodingKey {
        case id, name, team, position, number, appearances, minutes, goals, assists
        case photoURL = "photo_url"
        case yellowCards = "yellow_cards"
        case redCards = "red_cards"
        case averageRating = "average_rating"
    }
}

struct RankedItem: Identifiable, Hashable {
    let id: String
    let name: String
    let count: Int
}
