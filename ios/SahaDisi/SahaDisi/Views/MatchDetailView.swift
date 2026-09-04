import SwiftUI

struct MatchDetailView: View {
    @EnvironmentObject var store: AppStore
    let match: Match
    @State private var filter = "Tümü"

    private var exactRows: [Statement] {
        (store.payload?.statements ?? [])
            .filter { $0.matchId == match.id }
            .sorted { $0.date > $1.date }
    }

    private var contextualRows: [Statement] {
        guard exactRows.isEmpty else { return [] }
        return store.statements(matchID: match.id)
    }

    private var predictions: [Statement] { exactRows.filter { $0.type == "prediction" } }
    private var afterMatch: [Statement] { exactRows.filter { $0.type != "prediction" } }
    private var heroImageURL: String? {
        match.imageURL ?? exactRows.compactMap(\.imageURL).first ?? contextualRows.compactMap(\.imageURL).first
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                matchHeader

                if !exactRows.isEmpty {
                    filterBar
                    Text("Bu Maç İçin Yorumlar").font(.title3.bold())
                    ForEach(filteredRows) { statement in
                        NavigationLink(value: statement) {
                            matchComment(statement, contextLabel: statement.type == "prediction" ? "Maç Öncesi" : "Maç Sonrası")
                        }
                        .buttonStyle(.plain)
                    }
                } else if !contextualRows.isEmpty {
                    SDCard {
                        VStack(alignment: .leading, spacing: 6) {
                            Label("Bu maça doğrudan bağlanmış doğrulanmış yorum yok", systemImage: "info.circle")
                                .font(.subheadline.bold())
                            Text("Aşağıdakiler maç yorumu değildir; karşılaşmadaki takımlar hakkında yakın tarihte yapılmış doğrulanmış açıklamalardır.")
                                .font(.caption)
                                .foregroundStyle(SDTheme.muted)
                        }
                    }

                    Text("Takımlar Hakkındaki Güncel Yorumlar").font(.title3.bold())
                    ForEach(contextualRows) { statement in
                        NavigationLink(value: statement) {
                            matchComment(statement, contextLabel: teamContextLabel(statement))
                        }
                        .buttonStyle(.plain)
                    }
                } else {
                    SDCard {
                        VStack(alignment: .leading, spacing: 7) {
                            Text("Henüz doğrulanmış yorum yok").font(.headline)
                            Text("Bu maça doğrudan bağlanan güvenilir yorum geldiğinde burada görünecek.")
                                .font(.subheadline)
                                .foregroundStyle(SDTheme.muted)
                        }
                    }
                }
            }
            .padding(16)
        }
        .background(SDTheme.background)
        .navigationTitle("Maç Detayı")
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var filteredRows: [Statement] {
        if filter == "Maç Öncesi" { return predictions }
        if filter == "Maç Sonrası" { return afterMatch }
        return exactRows
    }

    private var matchHeader: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 20).fill(SDTheme.panel)
            if let heroImageURL, let url = URL(string: heroImageURL) {
                AsyncImage(url: url) { phase in
                    if case .success(let image) = phase {
                        image.resizable().scaledToFill().overlay(Color.black.opacity(0.55))
                    }
                }
                .clipShape(RoundedRectangle(cornerRadius: 20))
            }
            VStack(spacing: 14) {
                Text(SDDate.text(match.kickoff, includeTime: true))
                    .font(.caption)
                    .foregroundStyle(Color.white.opacity(0.72))
                HStack(spacing: 14) {
                    teamBlock(match.home, logo: match.homeLogoURL)
                    Text(score)
                        .font(.system(size: 38, weight: .black, design: .rounded))
                        .minimumScaleFactor(0.7)
                    teamBlock(match.away, logo: match.awayLogoURL)
                }
                Text("\(match.week). Hafta · \(match.league)")
                    .font(.caption)
                    .foregroundStyle(Color.white.opacity(0.72))
            }
            .padding(.vertical, 20)
            .padding(.horizontal, 8)
        }
        .frame(maxWidth: .infinity)
        .clipped()
    }

    private func teamBlock(_ name: String, logo: String?) -> some View {
        VStack(spacing: 8) {
            TeamLogoView(name: name, urlString: logo, size: 62)
            Text(name).font(.caption.bold()).multilineTextAlignment(.center).lineLimit(2)
        }
        .frame(maxWidth: .infinity)
    }

    private var filterBar: some View {
        HStack(spacing: 8) {
            ForEach(["Tümü", "Maç Öncesi", "Maç Sonrası"], id: \.self) { value in
                Button { filter = value } label: {
                    Text(value)
                        .font(.caption.bold())
                        .padding(.horizontal, 13)
                        .padding(.vertical, 8)
                        .foregroundStyle(filter == value ? Color.black : SDTheme.muted)
                        .background(filter == value ? Color.white : SDTheme.panel)
                        .clipShape(Capsule())
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func matchComment(_ statement: Statement, contextLabel: String) -> some View {
        let commentator = store.commentator(id: statement.commentator)
        return HStack(alignment: .top, spacing: 12) {
            AvatarView(text: commentator?.avatar ?? "?", size: 44, photoURL: commentator?.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                HStack {
                    Text(commentator?.name ?? statement.commentator).font(.subheadline.bold())
                    Text("·").foregroundStyle(SDTheme.muted2)
                    Text(contextLabel).font(.caption2).foregroundStyle(SDTheme.muted)
                    Spacer()
                    if statement.matchId == match.id { outcome(statement) }
                }
                Text("“\(statement.summary)”").font(.subheadline).lineLimit(5)
                Text(SDDate.text(statement.date)).font(.caption2).foregroundStyle(SDTheme.muted2)
            }
        }
        .padding(14)
        .background(SDTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: 15))
    }

    private func teamContextLabel(_ statement: Statement) -> String {
        guard let team = statement.team, !team.isEmpty else { return "Takım Gündemi" }
        return team
    }

    private func outcome(_ statement: Statement) -> some View {
        let text = statement.predictionOutcome == "correct" ? "DOĞRU" : (statement.predictionOutcome == "wrong" ? "YANLIŞ" : "")
        let color = statement.predictionOutcome == "correct" ? SDTheme.green : SDTheme.red
        return Text(text)
            .font(.caption2.black())
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .foregroundStyle(color)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(color.opacity(text.isEmpty ? 0 : 1)))
    }

    private var score: String {
        if let home = match.homeScore, let away = match.awayScore { return "\(home) - \(away)" }
        return "vs"
    }
}
