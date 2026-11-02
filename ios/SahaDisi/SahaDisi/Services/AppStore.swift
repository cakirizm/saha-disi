import Foundation

@MainActor
final class AppStore: ObservableObject {
    @Published var payload: FeedPayload?
    @Published var isLoading = true
    @Published var isRefreshing = false
    @Published var errorText: String?
    @Published var lastRefreshAt: Date?
    /// Answers every lookup below without touching the statements again.
    private var index = FeedIndex(nil)

    func bootstrap(forceRemote: Bool = false) async {
        if payload == nil { isLoading = true } else { isRefreshing = true }
        defer { isLoading = false; isRefreshing = false }
        do {
            let previousIDs = Set(payload?.statements.map(\.id) ?? [])
            let loaded = try await FeedService.shared.load(forceRemote: forceRemote)
            // A refresh that brings the same feed must not re-render every screen.
            if payload == nil || loaded.generatedAt != payload?.generatedAt {
                index = await FeedService.shared.index(for: loaded)
                payload = loaded
            }
            errorText = nil
            lastRefreshAt = Date()
            if !previousIDs.isEmpty {
                let fresh = loaded.statements.filter { !previousIDs.contains($0.id) }.sorted { $0.date > $1.date }
                await NotificationService.shared.deliverNewStatements(fresh, commentators: loaded.commentators)
            }
        } catch { errorText = error.localizedDescription }
    }

    func refresh() async { await bootstrap(forceRemote: true) }
    func commentator(id: String) -> Commentator? { index.commentators[id] }

    func logoURL(for team: String) -> String? { index.logos[canonicalTeam(team)] }

    func artworkURL(for team: String) -> String? {
        logoURL(for: team)
    }

    func statements(for commentatorID: String) -> [Statement] { index.byCommentator[commentatorID] ?? [] }

    func statements(for commentatorID: String, team: String) -> [Statement] {
        let target = canonicalTeam(team)
        return statements(for: commentatorID).filter { $0.team.map(canonicalTeam) == target }
    }

    /// A team page carries what the club's own page should: statements naming the
    /// club, plus statements from columns written about that club's matches. Two
    /// thirds of statements name no club on their own ("Kadıköy'de böyle
    /// oynayacağını düşünmezdim"), so filtering on the name alone left the page
    /// showing a fraction of the commentary that is actually about the team.
    func statements(team: String) -> [Statement] { index.byTeam[canonicalTeam(team)] ?? [] }

    /// Only statements whose own sentence names the club.
    func statements(naming team: String) -> [Statement] { index.byNamedTeam[canonicalTeam(team)] ?? [] }

    func statements(player: String) -> [Statement] { index.byPlayer[playerKey(player)] ?? [] }

    func playerKey(_ name: String) -> String { FeedIndex.playerKey(name) }

    func publications(player: String) -> [SourcePublication] {
        (payload?.publications ?? []).filter { $0.players.contains { playerKey($0) == playerKey(player) } }
    }

    func playerProfile(named name: String) -> PlayerProfile? { index.profiles[playerKey(name)] }

    func matchHistory(for player: String) -> [(Match, PlayerMatchRating)] {
        (payload?.matches ?? []).compactMap { match in
            match.playerRatings.first { $0.player.localizedCaseInsensitiveCompare(player) == .orderedSame }.map { (match, $0) }
        }.sorted { $0.0.kickoff > $1.0.kickoff }
    }

    func incidents(matchID: String) -> [Incident] { index.incidents[matchID] ?? [] }

    func statement(id: Int) -> Statement? { index.statementsByID[id] }

    func statements(matchID: String) -> [Statement] { index.byMatch[matchID] ?? [] }

    func relatedStatements(matchID: String) -> [Statement] {
        guard let match = payload?.matches?.first(where: { $0.id == matchID }) else { return [] }
        let exactIDs = Set(statements(matchID: matchID).map(\.id))
        return (statements(naming: match.home) + statements(naming: match.away))
            .filter { !exactIDs.contains($0.id) }
            .sorted { $0.date > $1.date }
    }

    var rankedTeams: [RankedItem] { index.rankedTeams }
    var rankedPlayers: [RankedItem] { index.rankedPlayers }
    var rankedCommentators: [(Commentator, Int)] { index.rankedCommentators }
    var commentatorFeedSections: [CommentatorFeedSection] { index.commentatorSections }
    var featuredMatches: [Match] { index.featuredMatches }
    var recentMatches: [Match] { index.recentMatches }

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

    var hotStatements: [Statement] { index.hot }

    var latestStatements: [Statement] { index.latest }

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

    func canonicalTeam(_ value: String) -> String { FeedIndex.canonicalTeam(value) }
}
