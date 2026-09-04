import SwiftUI

struct MatchDetailView: View {
    @EnvironmentObject var store: AppStore
    let match: Match
    @State private var filter = "Tümü"
    private var rows: [Statement] { store.statements(matchID: match.id) }
    private var predictions: [Statement] { rows.filter { $0.type == "prediction" } }
    private var afterMatch: [Statement] { rows.filter { $0.type != "prediction" } }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                matchHeader
                filterBar
                Text("Yorumcular Ne Dedi?").font(.title3.bold())
                ForEach(filteredRows) { s in NavigationLink(value: s) { matchComment(s) }.buttonStyle(.plain) }
                if filteredRows.isEmpty { Text("Bu filtre için doğrulanmış kayıt yok.").font(.subheadline).foregroundStyle(SDTheme.muted) }
            }.padding(16)
        }.background(SDTheme.background).navigationTitle("Maç Detayı").navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var filteredRows: [Statement] {
        if filter == "Maç Öncesi" { return predictions }
        if filter == "Maç Sonrası" { return afterMatch }
        return rows
    }

    private var matchHeader: some View {
        VStack(spacing: 14) {
            Text(match.kickoff).font(.caption2).foregroundStyle(SDTheme.muted)
            HStack(spacing: 20) {
                teamBlock(match.home)
                Text(score).font(.system(size: 38, weight: .black, design: .rounded))
                teamBlock(match.away)
            }
            Text("Hafta \(match.week) · \(match.league)").font(.caption).foregroundStyle(SDTheme.muted)
        }.frame(maxWidth: .infinity).padding(.vertical, 18).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 20))
    }

    private func teamBlock(_ name: String) -> some View {
        VStack(spacing: 8) { ZStack { Circle().fill(SDTheme.panel2); Image(systemName: "shield.fill").foregroundStyle(SDTheme.accent) }.frame(width: 56, height: 56); Text(name).font(.caption.bold()).multilineTextAlignment(.center).lineLimit(2) }.frame(maxWidth: .infinity)
    }

    private var filterBar: some View {
        HStack(spacing: 8) { ForEach(["Tümü", "Maç Öncesi", "Maç Sonrası"], id: \.self) { f in Button { filter = f } label: { Text(f).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8).foregroundStyle(filter == f ? Color.black : SDTheme.muted).background(filter == f ? Color.white : SDTheme.panel).clipShape(Capsule()) }.buttonStyle(.plain) } }
    }

    private func matchComment(_ s: Statement) -> some View {
        HStack(alignment: .top, spacing: 12) {
            AvatarView(text: store.commentator(id: s.commentator)?.avatar ?? "?", size: 42)
            VStack(alignment: .leading, spacing: 7) {
                HStack { Text(store.commentator(id: s.commentator)?.name ?? s.commentator).font(.subheadline.bold()); Text("·").foregroundStyle(SDTheme.muted2); Text(s.type == "prediction" ? "Maç Öncesi" : "Maç Sonrası").font(.caption2).foregroundStyle(SDTheme.muted); Spacer(); outcome(s) }
                Text("“\(s.summary)”").font(.subheadline).lineLimit(4)
            }
        }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
    }

    private func outcome(_ s: Statement) -> some View {
        let text = s.predictionOutcome == "correct" ? "DOĞRU" : (s.predictionOutcome == "wrong" ? "YANLIŞ" : "")
        let color = s.predictionOutcome == "correct" ? SDTheme.green : SDTheme.red
        return Text(text).font(.caption2.black()).padding(.horizontal, 6).padding(.vertical, 3).foregroundStyle(color).overlay(RoundedRectangle(cornerRadius: 4).stroke(color.opacity(text.isEmpty ? 0 : 1)))
    }
    private var score: String { if let h=match.homeScore, let a=match.awayScore { return "\(h) - \(a)" }; return "vs" }
}
