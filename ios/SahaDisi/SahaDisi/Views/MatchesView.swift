import SwiftUI

struct MatchesView: View {
    @EnvironmentObject var store: AppStore
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack { Text("Maçlar").font(.largeTitle.black()); Spacer(); TagPill(text: "Süper Lig") }
                Text("Maç önü tahminler ve maç sonrası yorumlar").font(.subheadline).foregroundStyle(SDTheme.muted)
                ForEach(store.payload?.matches ?? []) { match in
                    let linked = store.statements(matchID: match.id)
                    NavigationLink { MatchDetailView(match: match) } label: {
                        VStack(spacing: 10) {
                            HStack { Text("Hafta \(match.week)").font(.caption2).foregroundStyle(SDTheme.muted); Spacer(); Text(match.kickoff).font(.caption2).foregroundStyle(SDTheme.muted2) }
                            HStack {
                                Text(match.home).font(.headline).frame(maxWidth: .infinity, alignment: .leading)
                                Text(score(match)).font(.title2.black()).frame(width: 76)
                                Text(match.away).font(.headline).frame(maxWidth: .infinity, alignment: .trailing)
                            }
                            HStack { Label("\(linked.count) yorum", systemImage: "quote.bubble").font(.caption).foregroundStyle(linked.isEmpty ? SDTheme.muted : SDTheme.accent); Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2) }
                        }.padding(15).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                    }.buttonStyle(.plain)
                }
            }.padding(16)
        }.background(SDTheme.background).toolbar(.hidden, for: .navigationBar).refreshable { await store.refresh() }
    }
    private func score(_ m: Match) -> String { if let h=m.homeScore, let a=m.awayScore { return "\(h) - \(a)" }; return "vs" }
}
