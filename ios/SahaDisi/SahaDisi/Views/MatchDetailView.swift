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
                if !rows.isEmpty {
                    filterBar
                    Text("Yorumcular Ne Dedi?").font(.title3.bold())
                    ForEach(filteredRows) { s in NavigationLink(value: s) { matchComment(s) }.buttonStyle(.plain) }
                } else {
                    SDCard {
                        VStack(alignment: .leading, spacing: 7) {
                            Text("Henüz doğrulanmış yorum yok").font(.headline)
                            Text("Bu maça bağlanan güvenilir yorum geldiğinde burada görünecek.").font(.subheadline).foregroundStyle(SDTheme.muted)
                        }
                    }
                }
            }.padding(16)
        }
        .background(SDTheme.background).navigationTitle("Maç Detayı").navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var filteredRows: [Statement] {
        if filter == "Maç Öncesi" { return predictions }
        if filter == "Maç Sonrası" { return afterMatch }
        return rows
    }

    private var matchHeader: some View {
        VStack(spacing: 14) {
            Text(SDDate.text(match.kickoff, includeTime: true)).font(.caption).foregroundStyle(SDTheme.muted)
            HStack(spacing: 14) {
                teamBlock(match.home, logo: match.homeLogoURL)
                Text(score).font(.system(size: 38, weight: .black, design: .rounded)).minimumScaleFactor(0.7)
                teamBlock(match.away, logo: match.awayLogoURL)
            }
            Text("\(match.week). Hafta · \(match.league)").font(.caption).foregroundStyle(SDTheme.muted)
        }.frame(maxWidth: .infinity).padding(.vertical, 20).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 20))
    }

    private func teamBlock(_ name: String, logo: String?) -> some View {
        VStack(spacing: 8) {
            TeamLogoView(name: name, urlString: logo, size: 62)
            Text(name).font(.caption.bold()).multilineTextAlignment(.center).lineLimit(2)
        }.frame(maxWidth: .infinity)
    }

    private var filterBar: some View {
        HStack(spacing: 8) {
            ForEach(["Tümü", "Maç Öncesi", "Maç Sonrası"], id: \.self) { f in
                Button { filter = f } label: {
                    Text(f).font(.caption.bold()).padding(.horizontal, 13).padding(.vertical, 8)
                        .foregroundStyle(filter == f ? Color.black : SDTheme.muted)
                        .background(filter == f ? Color.white : SDTheme.panel).clipShape(Capsule())
                }.buttonStyle(.plain)
            }
        }
    }

    private func matchComment(_ s: Statement) -> some View {
        let c = store.commentator(id: s.commentator)
        return HStack(alignment: .top, spacing: 12) {
            AvatarView(text: c?.avatar ?? "?", size: 44, photoURL: c?.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                HStack {
                    Text(c?.name ?? s.commentator).font(.subheadline.bold())
                    Text("·").foregroundStyle(SDTheme.muted2)
                    Text(s.type == "prediction" ? "Maç Öncesi" : "Maç Sonrası").font(.caption2).foregroundStyle(SDTheme.muted)
                    Spacer(); outcome(s)
                }
                Text("“\(s.summary)”").font(.subheadline).lineLimit(5)
                Text(SDDate.text(s.date)).font(.caption2).foregroundStyle(SDTheme.muted2)
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
