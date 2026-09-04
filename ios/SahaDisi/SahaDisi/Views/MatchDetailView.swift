import SwiftUI

struct MatchDetailView: View {
    @EnvironmentObject var store: AppStore
    let match: Match
    @State private var filter = "Tümü"
    private var rows: [Statement] { store.statements(matchID: match.id) }
    private var relatedRows: [Statement] { Array(store.relatedStatements(matchID: match.id).prefix(8)) }
    private var predictions: [Statement] { rows.filter { $0.type == "prediction" } }
    private var afterMatch: [Statement] { rows.filter { $0.type != "prediction" } }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                MatchPoster(match: match).frame(height: 190).clipShape(RoundedRectangle(cornerRadius: 20))
                matchMeta
                if !rows.isEmpty {
                    filterBar
                    Text("Bu Maça Bağlı Yorumlar").font(.title3.bold())
                    ForEach(filteredRows) { s in NavigationLink(value: s) { matchComment(s, contextual: false) }.buttonStyle(.plain) }
                } else {
                    SDCard { VStack(alignment: .leading, spacing: 7) { Text("Henüz bu maça bağlı doğrulanmış yorum yok").font(.headline); Text("Sadece gerçekten bu maça bağlanmış yorumlar burada gösterilir.").font(.subheadline).foregroundStyle(SDTheme.muted) } }
                }
                if !relatedRows.isEmpty {
                    Text("Takımlar Hakkındaki Güncel Yorumlar").font(.title3.bold())
                    Text("Bunlar bu maça aitmiş gibi gösterilmez; yalnızca iki takım hakkında yakın dönem doğrulanmış sözlerdir.").font(.caption).foregroundStyle(SDTheme.muted)
                    ForEach(relatedRows) { s in NavigationLink(value: s) { matchComment(s, contextual: true) }.buttonStyle(.plain) }
                }
            }.padding(16)
        }
        .background(SDTheme.background).navigationTitle("Maç Detayı").navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var matchMeta: some View {
        VStack(spacing: 8) {
            HStack { Text(match.home).font(.title3.black()); Spacer(); Text(score).font(.title.black()); Spacer(); Text(match.away).font(.title3.black()) }
            Text("\(SDDate.text(match.kickoff, includeTime: true)) · \(match.league)").font(.caption).foregroundStyle(SDTheme.muted)
        }.padding(.horizontal, 4)
    }

    private var filteredRows: [Statement] {
        if filter == "Maç Öncesi" { return predictions }
        if filter == "Maç Sonrası" { return afterMatch }
        return rows
    }

    private var filterBar: some View {
        HStack(spacing: 8) {
            ForEach(["Tümü", "Maç Öncesi", "Maç Sonrası"], id: \.self) { f in
                Button { filter = f } label: { Text(f).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8).foregroundStyle(filter == f ? Color.black : SDTheme.muted).background(filter == f ? Color.white : SDTheme.panel).clipShape(Capsule()) }.buttonStyle(.plain)
            }
        }
    }

    private func matchComment(_ s: Statement, contextual: Bool) -> some View {
        let c = store.commentator(id: s.commentator)
        return HStack(alignment: .top, spacing: 12) {
            AvatarView(text: c?.avatar ?? "?", size: 44, photoURL: c?.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                HStack { Text(c?.name ?? s.commentator).font(.subheadline.bold()); Spacer(); Text(contextual ? "Takım yorumu" : (s.type == "prediction" ? "Maç Öncesi" : "Maç Sonrası")).font(.caption2).foregroundStyle(SDTheme.muted) }
                Text("“\(s.summary)”").font(.subheadline).lineLimit(5)
                HStack { Text(SDDate.text(s.date)).font(.caption2).foregroundStyle(SDTheme.muted2); Spacer(); if let team=s.team { Text(store.canonicalTeam(team)).font(.caption2).foregroundStyle(SDTheme.accent) } }
            }
        }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
    }

    private var score: String { if let h=match.homeScore, let a=match.awayScore { return "\(h) - \(a)" }; return "VS" }
}
