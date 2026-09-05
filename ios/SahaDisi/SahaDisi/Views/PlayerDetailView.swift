import SwiftUI

struct PlayerDetailView: View {
    @EnvironmentObject var store: AppStore
    let player: String
    @State private var selectedTab = "Yorumlar"
    private var profile: PlayerProfile? { store.playerProfile(named: player) }
    private var rows: [Statement] { store.statements(player: player) }
    private var history: [(Match, PlayerMatchRating)] { store.matchHistory(for: player) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                hero; tabBar
                if selectedTab == "Yorumlar" { comments }
                else if selectedTab == "Maçlar" { matches }
                else { statistics }
            }.padding(.horizontal, 16).padding(.bottom, 28)
        }.background(SDTheme.background).navigationTitle(player).navigationBarTitleDisplayMode(.inline)
    }

    private var hero: some View {
        SDCard {
            HStack(spacing: 16) {
                AsyncImage(url: URL(string: profile?.photoURL ?? "")) { phase in
                    if case .success(let image) = phase { image.resizable().scaledToFill() }
                    else { ZStack { Color.white.opacity(0.06); Image(systemName: "figure.soccer").font(.system(size: 42)).foregroundStyle(SDTheme.muted) } }
                }.frame(width: 94, height: 112).clipShape(RoundedRectangle(cornerRadius: 18))
                VStack(alignment: .leading, spacing: 7) {
                    Text(player).font(.title2.black())
                    if let team = profile?.team { NavigationLink(team) { TeamDetailView(team: team) }.font(.subheadline.bold()).foregroundStyle(SDTheme.accent) }
                    Text([profile?.position, profile?.number.map { "#\($0)" }].compactMap { $0 }.joined(separator: " · ")).font(.caption).foregroundStyle(SDTheme.muted)
                    Text("\(rows.count) tarihli yorum · \(Set(rows.map(\.commentator)).count) yorumcu").font(.caption).foregroundStyle(SDTheme.muted)
                }; Spacer()
            }
        }
    }

    private var tabBar: some View { HStack(spacing: 8) { tab("Yorumlar"); tab("Maçlar"); tab("İstatistik") } }
    private func tab(_ title: String) -> some View {
        Button { selectedTab = title } label: {
            Text(title).font(.caption.bold()).frame(maxWidth: .infinity).padding(.vertical, 10)
                .foregroundStyle(selectedTab == title ? Color.black : SDTheme.muted)
                .background(selectedTab == title ? Color.white : SDTheme.panel).clipShape(Capsule())
        }.buttonStyle(.plain)
    }

    private var comments: some View {
        VStack(alignment: .leading, spacing: 13) {
            Text("Kim, hangi gün ne dedi?").font(.title3.bold())
            if rows.isEmpty { empty("Bu oyuncu hakkında henüz kaynaklı yorum bulunamadı.") }
            ForEach(rows) { statement in
                NavigationLink { StatementDetailView(statement: statement) } label: {
                    let commentator = store.commentator(id: statement.commentator)
                    VStack(alignment: .leading, spacing: 9) {
                        HStack { AvatarView(text: commentator?.avatar ?? "?", size: 36, photoURL: commentator?.photoURL); Text(commentator?.name ?? statement.commentator).font(.subheadline.bold()); Spacer(); Text(SDDate.text(statement.date)).font(.caption2).foregroundStyle(SDTheme.muted) }
                        Text("“\(statement.summary)”").font(.body).lineSpacing(3).multilineTextAlignment(.leading)
                        HStack { Label(statement.source, systemImage: "link"); Spacer(); Text(statement.topic) }.font(.caption2).foregroundStyle(SDTheme.muted)
                    }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                }.buttonStyle(.plain)
            }
        }
    }

    private var matches: some View {
        VStack(alignment: .leading, spacing: 13) {
            Text("Maç performansları").font(.title3.bold())
            if history.isEmpty { empty("Maç bazlı oyuncu verisi henüz sağlayıcıdan gelmedi. Yorum geçmişi kullanılmaya devam ediyor.") }
            ForEach(history.indices, id: \.self) { index in
                let (match, rating) = history[index]
                NavigationLink { MatchDetailView(match: match) } label: {
                    HStack { VStack(alignment: .leading) { Text("\(match.home) – \(match.away)").font(.headline); Text(SDDate.text(match.kickoff, includeTime: true)).font(.caption).foregroundStyle(SDTheme.muted) }; Spacer(); if let value = rating.rating { Text(String(format: "%.1f", value)).font(.title3.black()).foregroundStyle(value >= 7 ? .green : .white) } }
                        .padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
                }.buttonStyle(.plain)
            }
        }
    }

    private var statistics: some View {
        VStack(alignment: .leading, spacing: 13) {
            Text("Sezon istatistikleri").font(.title3.bold())
            if let p = profile, [p.appearances, p.minutes, p.goals, p.assists].contains(where: { $0 != nil }) {
                LazyVGrid(columns: [.init(.flexible()), .init(.flexible())], spacing: 10) {
                    stat("Maç", p.appearances); stat("Dakika", p.minutes); stat("Gol", p.goals); stat("Asist", p.assists); stat("Sarı Kart", p.yellowCards); stat("Kırmızı Kart", p.redCards)
                    if let rating = p.averageRating { statText("Ortalama Puan", String(format: "%.2f", rating)) }
                }
            } else { empty("Gol, asist, dakika ve oyuncu puanları için doğrulanmış istatistik sağlayıcısı bekleniyor.") }
        }
    }

    private func stat(_ title: String, _ value: Int?) -> some View { statText(title, value.map(String.init) ?? "—") }
    private func statText(_ title: String, _ value: String) -> some View { VStack(spacing: 5) { Text(value).font(.title2.black()); Text(title).font(.caption).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity).padding(15).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14)) }
    private func empty(_ text: String) -> some View { SDCard { Label(text, systemImage: "chart.bar.doc.horizontal").font(.subheadline).foregroundStyle(SDTheme.muted) } }
}
