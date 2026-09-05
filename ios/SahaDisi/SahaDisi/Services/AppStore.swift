import Foundation

@MainActor
final class AppStore: ObservableObject {
    @Published var payload: FeedPayload?
    @Published var isLoading = true
    @Published var isRefreshing = false
    @Published var errorText: String?
    @Published var lastRefreshAt: Date?

    func bootstrap(forceRemote: Bool = false) async {
        if payload == nil { isLoading = true } else { isRefreshing = true }
        defer { isLoading = false; isRefreshing = false }
        do {
            let previousIDs = Set(payload?.statements.map(\.id) ?? [])
            let loaded = try await FeedService.shared.load(forceRemote: forceRemote)
            payload = loaded
            errorText = nil
            lastRefreshAt = Date()
            if !previousIDs.isEmpty {
                let fresh = loaded.statements.filter { !previousIDs.contains($0.id) }.sorted { $0.date > $1.date }
                await NotificationService.shared.deliverNewStatements(fresh, commentators: loaded.commentators)
            }
        } catch { errorText = error.localizedDescription }
    }

    func refresh() async { await bootstrap(forceRemote: true) }
    func commentator(id: String) -> Commentator? { payload?.commentators.first { $0.id == id } }

    func logoURL(for team: String) -> String? {
        let target = canonicalTeam(team)
        for match in payload?.matches ?? [] {
            if canonicalTeam(match.home) == target, let url = match.homeLogoURL { return url }
            if canonicalTeam(match.away) == target, let url = match.awayLogoURL { return url }
        }
        return nil
    }

    func artworkURL(for team: String) -> String? {
        logoURL(for: team)
    }

    func statements(for commentatorID: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.commentator == commentatorID }.sorted { $0.date > $1.date }
    }

    func statements(for commentatorID: String, team: String) -> [Statement] {
        let target = canonicalTeam(team)
        return (payload?.statements ?? []).filter {
            $0.commentator == commentatorID && $0.team.map(canonicalTeam) == target
        }.sorted { $0.date > $1.date }
    }

    func statements(team: String) -> [Statement] {
        let target = canonicalTeam(team)
        return (payload?.statements ?? []).filter { $0.team.map(canonicalTeam) == target }.sorted { $0.date > $1.date }
    }

    func statements(player: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.players.contains { $0.localizedCaseInsensitiveCompare(player) == .orderedSame } }.sorted { $0.date > $1.date }
    }

    func playerProfile(named name: String) -> PlayerProfile? {
        payload?.players?.first { $0.name.localizedCaseInsensitiveCompare(name) == .orderedSame }
    }

    func matchHistory(for player: String) -> [(Match, PlayerMatchRating)] {
        (payload?.matches ?? []).compactMap { match in
            match.playerRatings.first { $0.player.localizedCaseInsensitiveCompare(player) == .orderedSame }.map { (match, $0) }
        }.sorted { $0.0.kickoff > $1.0.kickoff }
    }

    func statements(matchID: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.matchId == matchID }.sorted { $0.date > $1.date }
    }

    func relatedStatements(matchID: String) -> [Statement] {
        guard let match = payload?.matches?.first(where: { $0.id == matchID }) else { return [] }
        let clubs = Set([canonicalTeam(match.home), canonicalTeam(match.away)])
        let exactIDs = Set(statements(matchID: matchID).map(\.id))
        return (payload?.statements ?? []).filter { row in
            guard !exactIDs.contains(row.id), let team = row.team else { return false }
            return clubs.contains(canonicalTeam(team))
        }.sorted { $0.date > $1.date }
    }

    var rankedTeams: [RankedItem] {
        let names = payload?.statements.compactMap { $0.team.map(canonicalTeam) } ?? []
        let grouped = Dictionary(grouping: names, by: { $0 })
        return grouped.map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }.sorted { $0.count > $1.count }
    }

    var rankedPlayers: [RankedItem] {
        let all = payload?.statements.flatMap(\.players) ?? []
        let grouped = Dictionary(grouping: all, by: { $0 })
        return grouped.map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }.sorted { $0.count > $1.count }
    }

    var rankedCommentators: [(Commentator, Int)] {
        (payload?.commentators ?? []).map { ($0, statements(for: $0.id).count) }.sorted { $0.1 > $1.1 }
    }

    func commentatorRanking(for team: String) -> [(Commentator, Int)] {
        let grouped = Dictionary(grouping: statements(team: team), by: \.commentator)
        return grouped.compactMap { id, values in commentator(id: id).map { ($0, values.count) } }.sorted { $0.1 > $1.1 }
    }

    func commentatorRanking(forPlayer player: String) -> [(Commentator, Int)] {
        let grouped = Dictionary(grouping: statements(player: player), by: \.commentator)
        return grouped.compactMap { id, values in commentator(id: id).map { ($0, values.count) } }.sorted { $0.1 > $1.1 }
    }

    func topTeams(for commentatorID: String) -> [RankedItem] {
        let all = statements(for: commentatorID).compactMap { $0.team.map(canonicalTeam) }
        return Dictionary(grouping: all, by: { $0 }).map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }.sorted { $0.count > $1.count }
    }

    func sentimentCounts(_ rows: [Statement]) -> (positive: Int, neutral: Int, negative: Int) {
        (rows.filter { $0.sentiment == "positive" }.count, rows.filter { $0.sentiment == "neutral" }.count, rows.filter { $0.sentiment == "negative" }.count)
    }

    func predictionStats(for commentatorID: String) -> (total: Int, correct: Int, wrong: Int) {
        let rows = statements(for: commentatorID).filter { $0.type == "prediction" && $0.predictionOutcome != nil }
        return (rows.count, rows.filter { $0.predictionOutcome == "correct" }.count, rows.filter { $0.predictionOutcome == "wrong" }.count)
    }

    var hotStatements: [Statement] {
        (payload?.statements ?? []).sorted {
            if $0.strength == $1.strength { return $0.date > $1.date }
            return $0.strength > $1.strength
        }
    }

    var latestStatements: [Statement] {
        (payload?.statements ?? []).sorted { $0.date > $1.date }
    }

    /// Feed items grouped by shared stance (topic + team + sentiment). A bucket
    /// with 2+ distinct commentators becomes a cluster (one strongest statement
    /// per commentator); everything else stays as individual single-item groups.
    var groupedFeed: [StatementGroup] {
        var order: [String] = []
        var buckets: [String: [Statement]] = [:]
        for s in latestStatements {
            let team = s.team.map(canonicalTeam) ?? "—"
            let key = "\(s.topic)||\(team)||\(s.sentiment)"
            if buckets[key] == nil { order.append(key) }
            buckets[key, default: []].append(s)
        }
        func byStrength(_ a: Statement, _ b: Statement) -> Bool {
            a.strength == b.strength ? a.date > b.date : a.strength > b.strength
        }
        // Generic "Genel yorum" is a catch-all: clustering on it lumps unrelated
        // takes together ("10 yorumcu aynı görüşte" on nothing in common). Only
        // let a specific, shared topic form a cluster.
        let genericTopics: Set<String> = ["Genel yorum", "Genel"]
        var result: [StatementGroup] = []
        for key in order {
            let sorted = buckets[key]!.sorted(by: byStrength)
            var seen = Set<String>()
            var perCommentator: [Statement] = []
            for s in sorted where seen.insert(s.commentator).inserted { perCommentator.append(s) }
            let isSpecificTopic = !genericTopics.contains(perCommentator.first?.topic ?? "Genel yorum")
            if perCommentator.count >= 2 && isSpecificTopic {
                let lead = perCommentator[0]
                result.append(StatementGroup(id: key, topic: lead.topic, team: lead.team, sentiment: lead.sentiment, statements: perCommentator))
            } else {
                for s in sorted {
                    result.append(StatementGroup(id: "single-\(s.id)", topic: s.topic, team: s.team, sentiment: s.sentiment, statements: [s]))
                }
            }
        }
        return result.sorted { $0.date > $1.date }
    }

    func canonicalTeam(_ value: String) -> String {
        let key = value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased(with: Locale(identifier: "tr_TR"))
        let aliases: [String:String] = [
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
        return aliases[key] ?? value
    }
}
