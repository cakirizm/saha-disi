import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var store: AppStore
    @State private var selectedWeek: Int?

    private var matches: [Match] { (store.payload?.matches ?? []).sorted { ($0.week, $0.kickoff) < ($1.week, $1.kickoff) } }
    private var weeks: [Int] { Array(Set(matches.map(\.week))).sorted() }
    private var currentWeek: Int? {
        let now = Date()
        let dated = matches.compactMap { match -> (Int, Date)? in
            guard let date = parseDate(match.kickoff) else { return nil }
            return (match.week, date)
        }
        if let nearest = dated.min(by: { abs($0.1.timeIntervalSince(now)) < abs($1.1.timeIntervalSince(now)) }) { return nearest.0 }
        let withScores = matches.filter { $0.homeScore != nil && $0.awayScore != nil }.map(\.week)
        return withScores.max() ?? weeks.first
    }
    private var visibleMatches: [Match] {
        guard let selectedWeek else { return matches }
        return matches.filter { $0.week == selectedWeek }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack { Text("Maçlar").font(.largeTitle.black()); Spacer(); TagPill(text: "Süper Lig") }
                Text("TFF fikstürü · geçmiş ve gelecek haftalar").font(.subheadline).foregroundStyle(SDTheme.muted)
                weekPicker

                if visibleMatches.isEmpty {
                    ContentUnavailableView("Maç bulunamadı", systemImage: "sportscourt", description: Text("Fikstür güncellenirken tekrar deneyin."))
                } else {
                    ForEach(weeksToShow, id: \.self) { week in
                        VStack(alignment: .leading, spacing: 10) {
                            Text("\(week). Hafta").font(.title3.bold()).padding(.top, 4)
                            ForEach(sortedMatches(in: week)) { match in matchCard(match) }
                        }
                    }
                }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
        .onAppear { if selectedWeek == nil { selectedWeek = currentWeek } }
    }

    private var weeksToShow: [Int] { selectedWeek.map { [$0] } ?? weeks }

    private func sortedMatches(in week: Int) -> [Match] {
        visibleMatches.filter { $0.week == week }.sorted {
            let l = store.statements(matchID: $0.id).count
            let r = store.statements(matchID: $1.id).count
            if l != r { return l > r }
            return $0.kickoff < $1.kickoff
        }
    }

    private var weekPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Button { selectedWeek = nil } label: { weekChip("Tümü", active: selectedWeek == nil) }.buttonStyle(.plain)
                ForEach(weeks, id: \.self) { week in
                    Button { selectedWeek = week } label: { weekChip("\(week). Hafta", active: selectedWeek == week) }.buttonStyle(.plain)
                }
            }
        }
    }

    private func weekChip(_ text: String, active: Bool) -> some View {
        Text(text).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8)
            .foregroundStyle(active ? Color.black : SDTheme.muted)
            .background(active ? Color.white : SDTheme.panel).clipShape(Capsule())
    }

    private func matchCard(_ match: Match) -> some View {
        let linked = store.statements(matchID: match.id)
        return NavigationLink { MatchDetailView(match: match) } label: {
            VStack(spacing: 0) {
                HStack(spacing: 18) {
                    TeamLogoView(name: match.home, urlString: match.homeLogoURL, size: 64)
                    VStack(spacing: 3) {
                        Text(score(match)).font(.title2.black())
                        Text(linked.isEmpty ? "Henüz yorum yok" : "\(linked.count) doğrulanmış yorum").font(.caption2).foregroundStyle(linked.isEmpty ? SDTheme.muted2 : SDTheme.accent)
                    }.frame(maxWidth: .infinity)
                    TeamLogoView(name: match.away, urlString: match.awayLogoURL, size: 64)
                }.padding(.top, 14).padding(.horizontal, 18)

                VStack(spacing: 10) {
                    HStack {
                        Text(SDDate.text(match.kickoff, includeTime: true)).font(.caption2).foregroundStyle(SDTheme.muted2)
                        Spacer(); Text("\(match.week). Hafta").font(.caption2).foregroundStyle(SDTheme.muted)
                    }
                    HStack {
                        Text(match.home).font(.headline).frame(maxWidth: .infinity, alignment: .leading)
                        Text("-").foregroundStyle(SDTheme.muted2)
                        Text(match.away).font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
                    }
                    HStack {
                        if !linked.isEmpty { Label("Yorumları gör", systemImage: "quote.bubble").font(.caption).foregroundStyle(SDTheme.accent) }
                        Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                    }
                }.padding(14)
            }
            .background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 17)).overlay(RoundedRectangle(cornerRadius: 17).stroke(SDTheme.line))
        }.buttonStyle(.plain)
    }

    private func parseDate(_ value: String) -> Date? {
        let iso = ISO8601DateFormatter()
        if let d = iso.date(from: value) { return d }
        let formats = ["yyyy-MM-dd", "dd.MM.yyyy HH:mm"]
        for format in formats {
            let formatter = DateFormatter(); formatter.locale = Locale(identifier: "tr_TR"); formatter.dateFormat = format
            if let d = formatter.date(from: value) { return d }
        }
        return nil
    }

    private func score(_ m: Match) -> String { if let h = m.homeScore, let a = m.awayScore { return "\(h) - \(a)" }; return "vs" }
}
