import SwiftUI

struct PlayerDetailView: View {
    @EnvironmentObject var store: AppStore
    let player: String
    @State private var selectedTab = "Yorumlar"

    private var rows: [Statement] { store.statements(player: player) }
    private var sentiment: (positive: Int, neutral: Int, negative: Int) { store.sentimentCounts(rows) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                hero
                tabBar
                if selectedTab == "Yorumlar" { comments }
                else { stats }
            }.padding(.horizontal, 16).padding(.bottom, 24)
        }
        .background(SDTheme.background)
        .navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var hero: some View {
        ZStack(alignment: .bottomLeading) {
            LinearGradient(colors: [Color(red: 0.08, green: 0.12, blue: 0.17), SDTheme.background], startPoint: .top, endPoint: .bottom)
            VStack(alignment: .leading, spacing: 10) {
                Spacer()
                HStack(alignment: .bottom) {
                    ZStack { Circle().fill(SDTheme.panel2); Image(systemName: "figure.soccer").font(.system(size: 44)).foregroundStyle(Color.white.opacity(0.8)) }.frame(width: 96, height: 96)
                    VStack(alignment: .leading, spacing: 6) {
                        Text(player).font(.title2.black())
                        Text("Oyuncu gündemi").font(.caption).foregroundStyle(SDTheme.muted)
                    }
                    Spacer()
                    Button("Takip Et") {}.font(.caption.bold()).padding(.horizontal, 16).padding(.vertical, 8).background(SDTheme.accent).clipShape(Capsule())
                }
                HStack { metric("Bu hafta", rows.count); metric("Yorumcu", Set(rows.map(\.commentator)).count); metric("İddialı", rows.filter { $0.strength >= 8 }.count) }
            }.padding(16)
        }.frame(height: 230).clipShape(RoundedRectangle(cornerRadius: 22))
    }

    private var tabBar: some View {
        HStack(spacing: 24) {
            tab("Yorumlar"); tab("İstatistik"); tab("Kaynaklar")
        }.padding(.top, 2)
    }
    private func tab(_ text: String) -> some View {
        Button { selectedTab = text } label: {
            VStack(spacing: 7) { Text(text).font(.caption.bold()).foregroundStyle(selectedTab == text ? .white : SDTheme.muted); Capsule().fill(selectedTab == text ? SDTheme.accent : .clear).frame(height: 2) }
        }.buttonStyle(.plain)
    }

    private var comments: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("En Çok Konuşan Yorumcular").font(.title3.bold())
            let ranking = Array(store.commentatorRanking(forPlayer: player).prefix(6)); let maxCount = ranking.first?.1 ?? 1
            SDCard {
                VStack(spacing: 5) {
                    ForEach(Array(ranking.enumerated()), id: \.offset) { i, row in
                        NavigationLink { CommentatorProfileView(commentator: row.0) } label: { RankBar(rank: i + 1, name: row.0.name, count: row.1, maxCount: maxCount) }.buttonStyle(.plain)
                    }
                }
            }
            Text("Hakkında Söylenenler").font(.title3.bold())
            ForEach(rows) { s in NavigationLink(value: s) { StatementRow(statement: s) }.buttonStyle(.plain) }
        }
    }

    private var stats: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Hakkında Konuşulma").font(.title3.bold())
            HStack { metricBox("Pozitif", sentiment.positive); metricBox("Nötr", sentiment.neutral); metricBox("Eleştirel", sentiment.negative) }
            SDCard {
                VStack(alignment: .leading, spacing: 9) {
                    Text("Veri Özeti").font(.headline)
                    Text("\(rows.count) doğrulanmış bahis · \(Set(rows.map(\.commentator)).count) farklı yorumcu · \(rows.filter { $0.strength >= 8 }.count) yüksek iddia").font(.subheadline).foregroundStyle(SDTheme.muted)
                }
            }
        }
    }

    private func metric(_ title: String, _ value: Int) -> some View { VStack(spacing: 3) { Text("\(value)").font(.headline.black()); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity) }
    private func metricBox(_ title: String, _ value: Int) -> some View { VStack(spacing: 4) { Text("\(value)").font(.title2.black()); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity).padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 13)) }
}
