import SwiftUI

struct CommentatorProfileView: View {
    @EnvironmentObject var store: AppStore
    @StateObject private var notifications = NotificationService.shared
    let commentator: Commentator
    var teamFilter: String? = nil
    @State private var selectedTab = "Yorumlar"
    private let tabs = ["Yorumlar", "İstatistikler", "En Çok Konuştuğu", "Hakkında"]

    private var allStatements: [Statement] { store.statements(for: commentator.id) }
    private var statements: [Statement] {
        guard let teamFilter else { return allStatements }
        return allStatements.filter { $0.team == teamFilter }
    }
    private var topPlayers: [RankedItem] {
        let all = statements.flatMap(\.players)
        return Dictionary(grouping: all, by: { $0 }).map { RankedItem(id: $0.key, name: $0.key, count: $0.value.count) }.sorted { $0.count > $1.count }
    }
    private var predictions: (total: Int, correct: Int, wrong: Int) {
        let rows = statements.filter { $0.type == "prediction" && $0.predictionOutcome != nil }
        return (rows.count, rows.filter { $0.predictionOutcome == "correct" }.count, rows.filter { $0.predictionOutcome == "wrong" }.count)
    }
    private var successRate: Int { predictions.total == 0 ? 0 : Int((Double(predictions.correct) / Double(predictions.total)) * 100) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                profileHeader
                if let teamFilter {
                    Label("Sadece \(teamFilter) yorumları gösteriliyor", systemImage: "line.3.horizontal.decrease.circle.fill")
                        .font(.caption.bold()).foregroundStyle(SDTheme.accent)
                }
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
        HStack(alignment: .center, spacing: 15) {
            AvatarView(text: commentator.avatar, size: 92, photoURL: commentator.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                Text(commentator.name).font(.title2.weight(.black))
                Text(commentator.role).font(.caption).foregroundStyle(SDTheme.muted)
                Text(commentator.primarySource).font(.caption2).foregroundStyle(SDTheme.muted2)
                notificationMenu
            }
            Spacer()
        }.padding(.top, 8)
    }

    private var notificationMenu: some View {
        Menu {
            Button { Task { await notifications.toggleCommentator(commentator.id) } } label: {
                Label(notifications.isCommentatorEnabled(commentator.id) ? "Yorumcu bildirimini kapat" : "\(commentator.name) bildirimlerini aç", systemImage: "person.crop.circle.badge.checkmark")
            }
            if let teamFilter {
                Button { Task { await notifications.toggle(commentatorID: commentator.id, team: teamFilter) } } label: {
                    Label(notifications.isPairEnabled(commentator.id, team: teamFilter) ? "\(teamFilter) filtresini kapat" : "Sadece \(teamFilter) + \(commentator.name)", systemImage: "bell.and.waves.left.and.right")
                }
            }
            Button { Task { await notifications.setAll(!notifications.allEnabled) } } label: {
                Label(notifications.allEnabled ? "Tüm bildirimleri kapat" : "Tüm bildirimleri aç", systemImage: notifications.allEnabled ? "bell.slash.fill" : "bell.badge")
            }
        } label: {
            Label("Bildirimler", systemImage: notifications.isCommentatorEnabled(commentator.id) || notifications.allEnabled ? "bell.fill" : "bell")
                .font(.caption.bold()).padding(.horizontal, 14).padding(.vertical, 8).background(SDTheme.accent).foregroundStyle(.black).clipShape(Capsule())
        }
    }

    private var statsStrip: some View {
        HStack(spacing: 0) {
            stat(teamFilter == nil ? "Toplam Yorum" : "Takım Yorumu", statements.count, .white)
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
            Text(teamFilter.map { "\($0) Hakkındaki Yorumlar" } ?? "Son Yorumlar").font(.title3.bold())
            if statements.isEmpty { Text("Bu filtre için doğrulanmış kayıt henüz yok.").foregroundStyle(SDTheme.muted) }
            ForEach(statements) { s in
                NavigationLink(value: s) {
                    VStack(alignment: .leading, spacing: 9) {
                        HStack {
                            Text(SDDate.text(s.date)).font(.caption2).foregroundStyle(SDTheme.muted)
                            Text("·").foregroundStyle(SDTheme.muted2)
                            Text(s.type == "prediction" ? "Maç Öncesi" : "Doğrulanmış söz").font(.caption2).foregroundStyle(SDTheme.muted)
                            Spacer(); predictionBadge(s)
                        }
                        Text("“\(s.summary)”").font(.subheadline.weight(.semibold)).lineLimit(5)
                        HStack {
                            if let team = s.team { Text(team).font(.caption).foregroundStyle(SDTheme.muted) }
                            Spacer(); Text(s.source).font(.caption2).foregroundStyle(SDTheme.muted2).lineLimit(1)
                        }
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
            let sourceRows = teamFilter == nil ? store.topTeams(for: commentator.id) : [RankedItem(id: teamFilter!, name: teamFilter!, count: statements.count)]
            let teamRows = Array(sourceRows.prefix(6)); let teamMax = teamRows.first?.count ?? 1
            SDCard { VStack { ForEach(Array(teamRows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: teamMax) }.buttonStyle(.plain) } } }
        }
    }

    private var aboutSection: some View {
        SDCard {
            VStack(alignment: .leading, spacing: 10) {
                Text(commentator.name).font(.headline)
                Text("Saha Dışı, kamuya açık kaynaklardan doğrulanmış doğrudan sözleri kısa ve kaynak bağlantılı biçimde gösterir. Ana kaynak: \(commentator.primarySource).").font(.subheadline).foregroundStyle(SDTheme.muted)
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
