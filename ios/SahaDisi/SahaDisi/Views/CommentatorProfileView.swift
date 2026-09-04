import SwiftUI

struct CommentatorProfileView: View {
    @EnvironmentObject var store: AppStore
    let commentator: Commentator
    @State private var selectedTab = "Yorumlar"
    private let tabs = ["Yorumlar", "İstatistikler", "En Çok Konuştuğu", "Hakkında"]

    private var statements: [Statement] { store.statements(for: commentator.id) }
    private var topPlayers: [RankedItem] {
        let all = statements.flatMap(\.players)
        return Dictionary(grouping: all, by: { $0 }).map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }.sorted { $0.count > $1.count }
    }
    private var predictions: (total: Int, correct: Int, wrong: Int) { store.predictionStats(for: commentator.id) }
    private var successRate: Int { predictions.total == 0 ? 0 : Int((Double(predictions.correct) / Double(predictions.total)) * 100) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                profileHeader
                statsStrip
                tabBar
                if selectedTab == "Yorumlar" { commentsSection }
                else if selectedTab == "İstatistikler" { statisticsSection }
                else if selectedTab == "En Çok Konuştuğu" { mostTalkedSection }
                else { aboutSection }
            }.padding(.horizontal, 16).padding(.bottom, 24)
        }
        .background(SDTheme.background)
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(SDTheme.background, for: .navigationBar)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var profileHeader: some View {
        HStack(alignment: .top, spacing: 14) {
            AvatarView(text: commentator.avatar, size: 88, photoURL: commentator.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                Text(commentator.name).font(.title2.weight(.black))
                Text("\(commentator.role) · \(commentator.primarySource)").font(.caption).foregroundStyle(SDTheme.muted)
                Button("Takip Et") {}.font(.caption.bold()).padding(.horizontal, 18).padding(.vertical, 8).background(SDTheme.accent).clipShape(Capsule())
            }
            Spacer()
            Image(systemName: "square.and.arrow.up").foregroundStyle(SDTheme.muted)
        }.padding(.top, 8)
    }

    private var statsStrip: some View {
        HStack(spacing: 0) {
            stat("Toplam Yorum", statements.count, .white)
            stat("Doğru Tahmin", predictions.correct, SDTheme.green)
            stat("Yanlış Tahmin", predictions.wrong, SDTheme.red)
            stat("Başarı Oranı", successRate, SDTheme.green, suffix: "%")
        }.padding(.vertical, 14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
    }

    private var tabBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 18) {
                ForEach(tabs, id: \.self) { tab in
                    Button { selectedTab = tab } label: {
                        VStack(spacing: 8) {
                            Text(tab).font(.caption.weight(selectedTab == tab ? .bold : .medium)).foregroundStyle(selectedTab == tab ? .white : SDTheme.muted)
                            Capsule().fill(selectedTab == tab ? SDTheme.accent : .clear).frame(height: 2)
                        }
                    }.buttonStyle(.plain)
                }
            }
        }
    }

    private var commentsSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Son Yorumlar").font(.title3.bold())
            if statements.isEmpty { Text("Bu yorumcu için doğrulanmış kayıt henüz yok.").foregroundStyle(SDTheme.muted) }
            ForEach(statements) { s in
                NavigationLink(value: s) {
                    VStack(alignment: .leading, spacing: 9) {
                        HStack { Text(s.date).font(.caption2).foregroundStyle(SDTheme.muted); Text("·"); Text(s.type == "prediction" ? "Maç Öncesi" : "Yorum").font(.caption2).foregroundStyle(SDTheme.muted); Spacer(); predictionBadge(s) }
                        Text("“\(s.summary)”").font(.subheadline.weight(.semibold)).lineLimit(5)
                        if let team = s.team { Text(team).font(.caption).foregroundStyle(SDTheme.muted) }
                    }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
                }.buttonStyle(.plain)
            }
        }
    }

    private var statisticsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Tahmin Performansı").font(.title3.bold())
            SDCard {
                VStack(alignment: .leading, spacing: 12) {
                    Text("%\(successRate) başarı").font(.title2.weight(.black)).foregroundStyle(successRate >= 50 ? SDTheme.green : SDTheme.red)
                    ProgressView(value: Double(successRate), total: 100).tint(SDTheme.accent)
                    Text("\(predictions.total) sonuçlanan tahmin · \(predictions.correct) doğru · \(predictions.wrong) yanlış").font(.caption).foregroundStyle(SDTheme.muted)
                }
            }
            let sentiments = store.sentimentCounts(statements)
            Text("Yorum Tonu").font(.title3.bold())
            HStack { smallMetric("Pozitif", sentiments.positive); smallMetric("Nötr", sentiments.neutral); smallMetric("Eleştirel", sentiments.negative) }
        }
    }

    private var mostTalkedSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("En Çok Konuştuğu Oyuncular").font(.title3.bold())
            let playerRows = Array(topPlayers.prefix(6)); let playerMax = playerRows.first?.count ?? 1
            SDCard { VStack { ForEach(Array(playerRows.enumerated()), id: \.element.id) { i, item in NavigationLink { PlayerDetailView(player: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: playerMax) }.buttonStyle(.plain) } } }
            Text("En Çok Konuştuğu Takımlar").font(.title3.bold())
            let teamRows = Array(store.topTeams(for: commentator.id).prefix(6)); let teamMax = teamRows.first?.count ?? 1
            SDCard { VStack { ForEach(Array(teamRows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: teamMax) }.buttonStyle(.plain) } } }
        }
    }

    private var aboutSection: some View {
        SDCard {
            VStack(alignment: .leading, spacing: 10) {
                Text(commentator.name).font(.headline)
                Text("Saha Dışı, kamuya açık kaynaklardan doğrulanmış yorumları yapılandırır. Kaynak: \(commentator.primarySource). Profilde yalnızca doğrulanmış kayıtlar gösterilir.").font(.subheadline).foregroundStyle(SDTheme.muted)
            }
        }
    }

    private func stat(_ title: String, _ value: Int, _ color: Color, suffix: String = "") -> some View {
        VStack(spacing: 4) { Text("\(value)\(suffix)").font(.title3.weight(.black)).foregroundStyle(color); Text(title).font(.system(size: 9)).foregroundStyle(SDTheme.muted).multilineTextAlignment(.center) }.frame(maxWidth: .infinity)
    }
    private func smallMetric(_ title: String, _ value: Int) -> some View { VStack(spacing: 4) { Text("\(value)").font(.title2.weight(.black)); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity).padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 13)) }
    private func predictionBadge(_ s: Statement) -> some View {
        let label = s.predictionOutcome == "correct" ? "DOĞRU" : (s.predictionOutcome == "wrong" ? "YANLIŞ" : "")
        let color = s.predictionOutcome == "correct" ? SDTheme.green : SDTheme.red
        return Text(label).font(.caption2.weight(.black)).padding(.horizontal, 7).padding(.vertical, 4).background(color.opacity(label.isEmpty ? 0 : 0.15)).foregroundStyle(color).clipShape(RoundedRectangle(cornerRadius: 4))
    }
}
