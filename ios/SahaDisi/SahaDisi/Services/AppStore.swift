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
            payload = try await FeedService.shared.load(forceRemote: forceRemote)
            errorText = nil
            lastRefreshAt = Date()
        } catch {
            errorText = error.localizedDescription
        }
    }

    func refresh() async { await bootstrap(forceRemote: true) }

    func commentator(id: String) -> Commentator? { payload?.commentators.first { $0.id == id } }

    func statements(for commentatorID: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.commentator == commentatorID }.sorted { $0.date > $1.date }
    }

    func statements(team: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.team == team }.sorted { $0.date > $1.date }
    }

    func statements(player: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.players.contains(player) }.sorted { $0.date > $1.date }
    }

    func statements(matchID: String) -> [Statement] {
        (payload?.statements ?? []).filter { $0.matchId == matchID }.sorted { $0.date > $1.date }
    }

    var rankedTeams: [RankedItem] {
        let grouped = Dictionary(grouping: payload?.statements.compactMap(\.team) ?? [], by: { $0 })
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
        let all = statements(for: commentatorID).compactMap(\.team)
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
}
