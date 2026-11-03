import Foundation

/// Every lookup the screens need, worked out once per feed away from the main
/// thread. SwiftUI re-evaluates view bodies constantly while scrolling, and each
/// of these used to scan and sort all statements on every evaluation: with ~4,500
/// statements one swipe of the home carousel blocked the main thread long enough
/// for iOS to kill the app.
struct FeedIndex {
    let latest: [Statement]
    let hot: [Statement]
    let commentators: [String: Commentator]
    let statementsByID: [Int: Statement]
    let byCommentator: [String: [Statement]]
    /// Statements whose own sentence names the club.
    let byNamedTeam: [String: [Statement]]
    /// Those plus statements from columns about the club's matches: the team page.
    let byTeam: [String: [Statement]]
    let byPlayer: [String: [Statement]]
    let byMatch: [String: [Statement]]
    let logos: [String: String]
    let profiles: [String: PlayerProfile]
    let incidents: [String: [Incident]]
    let rankedTeams: [RankedItem]
    let rankedPlayers: [RankedItem]
    let rankedCommentators: [(Commentator, Int)]
    let commentatorSections: [CommentatorFeedSection]
    let featuredMatches: [Match]
    let recentMatches: [Match]

    init(_ payload: FeedPayload?, now: Date = Date()) {
        let statements = payload?.statements ?? []
        let matches = payload?.matches ?? []
        let people = payload?.commentators ?? []

        let latest = statements.sorted { $0.date > $1.date }
        self.latest = latest
        hot = statements.sorted {
            if $0.strength == $1.strength { return $0.date > $1.date }
            return $0.strength > $1.strength
        }
        commentators = Dictionary(people.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        statementsByID = Dictionary(statements.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
        let byCommentator = Dictionary(grouping: latest, by: \.commentator)
        self.byCommentator = byCommentator

        var clubsByMatch: [String: [String]] = [:]
        var logos: [String: String] = [:]
        for match in matches {
            let home = FeedIndex.canonicalTeam(match.home)
            let away = FeedIndex.canonicalTeam(match.away)
            clubsByMatch[match.id] = [home, away]
            if logos[home] == nil, let url = match.homeLogoURL { logos[home] = url }
            if logos[away] == nil, let url = match.awayLogoURL { logos[away] = url }
        }
        self.logos = logos

        // Walking the newest-first list keeps every group below newest-first too.
        var named: [String: [Statement]] = [:]
        var teams: [String: [Statement]] = [:]
        var players: [String: [Statement]] = [:]
        var playerNames: [String: String] = [:]
        var byMatch: [String: [Statement]] = [:]
        for statement in latest {
            var clubs = Set<String>()
            if let team = statement.team {
                let club = FeedIndex.canonicalTeam(team)
                clubs.insert(club)
                named[club, default: []].append(statement)
            }
            if let id = statement.matchId {
                byMatch[id, default: []].append(statement)
                clubs.formUnion(clubsByMatch[id] ?? [])
            }
            for club in clubs { teams[club, default: []].append(statement) }

            var keys = Set<String>()
            for name in statement.players {
                let key = FeedIndex.playerKey(name)
                keys.insert(key)
                if let known = playerNames[key], known <= name { continue }
                playerNames[key] = name
            }
            for key in keys { players[key, default: []].append(statement) }
        }
        byNamedTeam = named
        byTeam = teams
        byPlayer = players
        self.byMatch = byMatch

        var profiles: [String: PlayerProfile] = [:]
        for profile in payload?.players ?? [] {
            let key = FeedIndex.playerKey(profile.name)
            if profiles[key] == nil { profiles[key] = profile }
        }
        self.profiles = profiles

        incidents = Dictionary(grouping: payload?.incidents ?? [], by: \.matchID)
            .mapValues { rows in rows.sorted { ($0.minute ?? 999) < ($1.minute ?? 999) } }

        rankedTeams = teams.map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }
            .sorted { $0.count == $1.count ? $0.name < $1.name : $0.count > $1.count }
        rankedPlayers = players.map { key, rows in
            RankedItem(id: key, name: playerNames[key] ?? key, count: rows.count)
        }.sorted { $0.count == $1.count ? $0.name < $1.name : $0.count > $1.count }
        rankedCommentators = people.map { ($0, byCommentator[$0.id]?.count ?? 0) }.filter { $0.1 > 0 }.sorted { $0.1 > $1.1 }

        commentatorSections = FeedIndex.sections(people: people, byCommentator: byCommentator, now: now)

        featuredMatches = Array(matches.sorted { a, b in
            let ac = byMatch[a.id]?.count ?? 0
            let bc = byMatch[b.id]?.count ?? 0
            if ac != bc { return ac > bc }
            return a.kickoff > b.kickoff
        }.prefix(4))
        recentMatches = Array(matches.filter { $0.homeScore != nil }.sorted { $0.kickoff > $1.kickoff }.prefix(4))
    }

    /// Activity in our feed, not an inferred platform-wide popularity score.
    private static func sections(people: [Commentator], byCommentator: [String: [Statement]], now: Date) -> [CommentatorFeedSection] {
        let cutoff = now.addingTimeInterval(-7 * 24 * 60 * 60)
        let iso = ISO8601DateFormatter()
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let day = DateFormatter()
        day.locale = Locale(identifier: "en_US_POSIX")
        day.timeZone = TimeZone(identifier: "Europe/Istanbul")
        day.dateFormat = "yyyy-MM-dd"
        // Columns share publication stamps, and parsing a date is the slow part.
        var parsed: [String: Date] = [:]
        func date(_ value: String) -> Date {
            if let known = parsed[value] { return known }
            let result = fractional.date(from: value) ?? iso.date(from: value) ?? day.date(from: value) ?? .distantPast
            parsed[value] = result
            return result
        }
        var sections: [CommentatorFeedSection] = []
        for person in people {
            guard let comments = byCommentator[person.id], !comments.isEmpty else { continue }
            let dated = comments.map { (statement: $0, date: date($0.date)) }
            let sorted = dated.sorted { $0.date == $1.date ? $0.statement.id > $1.statement.id : $0.date > $1.date }
            let recentCount = sorted.filter { $0.date >= cutoff && $0.date <= now }.count
            sections.append(CommentatorFeedSection(commentator: person, statements: sorted.map { $0.statement }, recentCount: recentCount, latestDate: sorted[0].date))
        }
        return sections.sorted {
            if $0.recentCount != $1.recentCount { return $0.recentCount > $1.recentCount }
            if $0.latestDate != $1.latestDate { return $0.latestDate > $1.latestDate }
            return $0.commentator.name < $1.commentator.name
        }
    }

    static func playerKey(_ name: String) -> String {
        let value = name.folding(options: [.caseInsensitive, .diacriticInsensitive], locale: Locale(identifier: "en_US_POSIX"))
            .split(whereSeparator: { $0.isWhitespace }).joined(separator: " ")
        return playerAliases[value] ?? value
    }

    private static let playerAliases = ["victor osimhen": "osimhen", "lucas torreira": "torreira", "rafael leao": "leao", "aleksey batrakov": "batrakov", "leroy sane": "sane", "anderson talisca": "talisca", "marco asensio": "asensio"]

    static func canonicalTeam(_ value: String) -> String {
        let key = value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased(with: Locale(identifier: "tr_TR"))
        return teamAliases[key] ?? value
    }

    private static let teamAliases: [String: String] = [
        "galatasaray a.ş.":"Galatasaray", "galatasaray":"Galatasaray", "fenerbahçe a.ş.":"Fenerbahçe", "fenerbahçe":"Fenerbahçe",
        "beşiktaş a.ş.":"Beşiktaş", "beşiktaş":"Beşiktaş", "trabzonspor a.ş.":"Trabzonspor", "trabzonspor":"Trabzonspor",
        "samsunspor a.ş.":"Samsunspor", "samsunspor":"Samsunspor", "göztepe a.ş.":"Göztepe", "göztepe":"Göztepe",
        "tümosan konyaspor":"Konyaspor", "konyaspor":"Konyaspor", "çaykur rizespor a.ş.":"Rizespor", "çaykur rizespor":"Rizespor", "rizespor":"Rizespor",
        "arca çorum fk":"Çorum FK", "çorum fk":"Çorum FK", "çorum":"Çorum FK", "gaziantep futbol kulübü a.ş.":"Gaziantep FK",
        "gaziantep futbol kulübü":"Gaziantep FK", "gaziantep fk":"Gaziantep FK", "gaziantep":"Gaziantep FK",
        "istanbul başakşehir fk":"Başakşehir", "istanbul başakşehir":"Başakşehir", "başakşehir":"Başakşehir",
        "amed sportif faaliyetler":"Amed SK", "amed":"Amed SK", "amed sk":"Amed SK", "erzurumspor fk":"Erzurumspor", "erzurumspor":"Erzurumspor",
        "corendon alanyaspor":"Alanyaspor", "alanyaspor":"Alanyaspor", "kasımpaşa a.ş.":"Kasımpaşa", "kasımpaşa":"Kasımpaşa",
        "kocaelispor":"Kocaelispor", "gençlerbirliği":"Gençlerbirliği", "eyüpspor":"Eyüpspor",
        "fenerbahce":"Fenerbahçe", "besiktas":"Beşiktaş", "goztepe":"Göztepe", "kasimpasa":"Kasımpaşa",
        "basaksehir":"Başakşehir", "istanbul basaksehir":"Başakşehir", "caykur rizespor":"Rizespor",
        "corum fk":"Çorum FK", "genclerbirligi":"Gençlerbirliği", "eyupspor":"Eyüpspor"
    ]
}
