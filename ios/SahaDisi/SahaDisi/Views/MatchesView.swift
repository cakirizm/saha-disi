import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var store: AppStore
    @State private var selectedWeek: Int?

    private var matches: [Match] { (store.payload?.matches ?? []).sorted { ($0.week, $0.kickoff) < ($1.week, $1.kickoff) } }
    private var weeks: [Int] { Array(Set(matches.map(\.week))).sorted() }
    private var visibleMatches: [Match] {
        guard let selectedWeek else { return matches }
        return matches.filter { $0.week == selectedWeek }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack { Text("Maçlar").font(.largeTitle.black()); Spacer(); TagPill(text: "Süper Lig") }
                Text("TFF haftalarına göre fikstür, skorlar ve maç yorumları").font(.subheadline).foregroundStyle(SDTheme.muted)
                weekPicker

                if visibleMatches.isEmpty {
                    ContentUnavailableView("Maç bulunamadı", systemImage: "sportscourt", description: Text("Fikstür güncellenirken tekrar deneyin."))
                } else {
                    ForEach(weeksToShow, id: \.self) { week in
                        VStack(alignment: .leading, spacing: 10) {
                            Text("\(week). Hafta").font(.title3.bold()).padding(.top, 4)
                            ForEach(visibleMatches.filter { $0.week == week }) { match in matchCard(match) }
                        }
                    }
                }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
        .onAppear {
            if selectedWeek == nil { selectedWeek = weeks.last }
        }
    }

    private var weeksToShow: [Int] {
        if let selectedWeek { return [selectedWeek] }
        return weeks
    }

    private var weekPicker: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                Button { selectedWeek = nil } label: { weekChip("Tümü", active: selectedWeek == nil) }.buttonStyle(.plain)
                ForEach(weeks, id: \.self) { week in
                    Button { selectedWeek = week } label: { weekChip("H\(week)", active: selectedWeek == week) }.buttonStyle(.plain)
                }
            }
        }
    }

    private func weekChip(_ text: String, active: Bool) -> some View {
        Text(text).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8)
            .foregroundStyle(active ? Color.black : SDTheme.muted)
            .background(active ? Color.white : SDTheme.panel)
            .clipShape(Capsule())
    }

    private func matchCard(_ match: Match) -> some View {
        let linked = store.statements(matchID: match.id)
        return NavigationLink { MatchDetailView(match: match) } label: {
            VStack(spacing: 0) {
                MatchArtwork(match: match).frame(height: 96)
                VStack(spacing: 10) {
                    HStack { Text(match.kickoff).font(.caption2).foregroundStyle(SDTheme.muted2); Spacer(); Text("TFF · \(match.week). Hafta").font(.caption2).foregroundStyle(SDTheme.muted) }
                    HStack {
                        Text(match.home).font(.headline).frame(maxWidth: .infinity, alignment: .leading)
                        Text(score(match)).font(.title2.black()).frame(width: 76)
                        Text(match.away).font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
                    }
                    HStack {
                        Label("\(linked.count) yorum", systemImage: "quote.bubble").font(.caption).foregroundStyle(linked.isEmpty ? SDTheme.muted : SDTheme.accent)
                        Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                    }
                }.padding(14)
            }
            .background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 17)).overlay(RoundedRectangle(cornerRadius: 17).stroke(SDTheme.line))
        }.buttonStyle(.plain)
    }

    private func score(_ m: Match) -> String { if let h = m.homeScore, let a = m.awayScore { return "\(h) - \(a)" }; return "vs" }
}
