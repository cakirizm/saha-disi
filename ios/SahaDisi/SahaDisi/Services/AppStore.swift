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

    func statements(for commentatorID: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.commentator == commentatorID }.sorted { $0.date > $1.date }
    }

    func statements(team: String) -> [Statement] {
        let target = canonicalTeam(team)
        return (payload?.statements ?? []).filter { row in
            guard let value = row.team else { return false }
            return canonicalTeam(value) == target
        }.sorted { $0.date > $1.date }
    }

    func statements(player: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.players.contains(player) }.sorted { $0.date > $1.date }
    }

    /// Exact match-linked comments first. If the collector could not attach a match id,
    /// show recent verified comments about either club around the fixture date instead of an empty page.
    func statements(matchID: String) -> [Statement] {
        let all = payload?.statements ?? []
        let exact = all.filter { $0.matchId == matchID }.sorted { $0.date > $1.date }
        if !exact.isEmpty { return exact }
        guard let match = payload?.matches?.first(where: { $0.id == matchID }) else { return [] }
        let clubs = Set([canonicalTeam(match.home), canonicalTeam(match.away)])
        let kickoff = parseDate(match.kickoff)
        return all.filter { row in
            guard let team = row.team, clubs.contains(canonicalTeam(team)) else { return false }
            guard let kickoff, let statementDate = parseDate(row.date) else { return true }
            return abs(statementDate.timeIntervalSince(kickoff)) <= 60 * 60 * 24 * 7
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

    private func canonicalTeam(_ value: String) -> String {
        let key = value.trimmingCharacters(in: .whitespacesAndNewlines).lowercased(with: Locale(identifier: "tr_TR"))
        let aliases: [String:String] = [
            "galatasaray a.ş.":"Galatasaray", "galatasaray":"Galatasaray",
            "fenerbahçe a.ş.":"Fenerbahçe", "fenerbahçe":"Fenerbahçe",
            "beşiktaş a.ş.":"Beşiktaş", "beşiktaş":"Beşiktaş",
            "trabzonspor a.ş.":"Trabzonspor", "trabzonspor":"Trabzonspor",
            "göztepe a.ş.":"Göztepe", "göztepe":"Göztepe",
            "tümosan konyaspor":"Konyaspor", "konyaspor":"Konyaspor",
            "çaykur rizespor":"Rizespor", "rizespor":"Rizespor",
            "arca çorum fk":"Çorum FK", "çorum fk":"Çorum FK", "çorum":"Çorum FK",
            "gaziantep futbol kulübü a.ş.":"Gaziantep FK", "gaziantep futbol kulübü":"Gaziantep FK", "gaziantep fk":"Gaziantep FK", "gaziantep":"Gaziantep FK",
            "istanbul başakşehir fk":"Başakşehir", "istanbul başakşehir":"Başakşehir", "başakşehir":"Başakşehir",
            "amed sportif faaliyetler":"Amed SK", "amed":"Amed SK", "amed sk":"Amed SK",
            "erzurumspor fk":"Erzurumspor", "erzurumspor":"Erzurumspor",
            "corendon alanyaspor":"Alanyaspor", "alanyaspor":"Alanyaspor"
        ]
        return aliases[key] ?? value
    }

    private func parseDate(_ value: String) -> Date? {
        let iso = ISO8601DateFormatter()
        if let d = iso.date(from: value) { return d }
        for format in ["yyyy-MM-dd", "dd.MM.yyyy HH:mm"] {
            let f = DateFormatter(); f.locale = Locale(identifier: "tr_TR"); f.dateFormat = format
            if let d = f.date(from: value) { return d }
        }
        return nil
    }
}
