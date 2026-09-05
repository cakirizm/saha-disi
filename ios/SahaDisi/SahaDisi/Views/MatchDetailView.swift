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
                matchCenter
                if !rows.isEmpty {
                    consensusSummary
                    filterBar
                    Text("Bu Maça Bağlı Yorumlar").font(.title3.bold())
                    ForEach(filteredRows) { s in NavigationLink { StatementDetailView(statement: s) } label: { matchComment(s, contextual: false) }.buttonStyle(.plain) }
                } else {
                    SDCard { VStack(alignment: .leading, spacing: 7) { Text("Henüz bu maça bağlı doğrulanmış yorum yok").font(.headline); Text("Sadece gerçekten bu maça bağlanmış yorumlar burada gösterilir.").font(.subheadline).foregroundStyle(SDTheme.muted) } }
                }
                if !relatedRows.isEmpty {
                    Text("Takımlar Hakkındaki Güncel Yorumlar").font(.title3.bold())
                    Text("Bunlar bu maça aitmiş gibi gösterilmez; yalnızca iki takım hakkında yakın dönem doğrulanmış sözlerdir.").font(.caption).foregroundStyle(SDTheme.muted)
                    ForEach(relatedRows) { s in NavigationLink { StatementDetailView(statement: s) } label: { matchComment(s, contextual: true) }.buttonStyle(.plain) }
                }
            }.padding(16)
        }
        .background(SDTheme.background).navigationTitle("Maç Detayı").navigationBarTitleDisplayMode(.inline)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var consensusSummary: some View {
        let s = store.sentimentCounts(rows)
        return SDCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Label("Yorumcu Konsensüsü", systemImage: "bubble.left.and.bubble.right.fill").font(.subheadline.bold())
                    Spacer()
                    Text("\(rows.count) yorumcu").font(.caption2).foregroundStyle(SDTheme.muted)
                }
                HStack(spacing: 8) {
                    consensusPill(SDTheme.green, "Olumlu", s.positive)
                    consensusPill(SDTheme.red, "Eleştirel", s.negative)
                    consensusPill(SDTheme.muted, "Nötr", s.neutral)
                }
            }
        }
    }

    private func consensusPill(_ color: Color, _ title: String, _ count: Int) -> some View {
        HStack(spacing: 5) {
            Circle().fill(color).frame(width: 8, height: 8)
            Text("\(title) \(count)").font(.caption2.weight(.semibold)).foregroundStyle(SDTheme.muted)
        }
        .padding(.horizontal, 10).padding(.vertical, 6)
        .background(color.opacity(0.12)).clipShape(Capsule())
    }

    private var matchMeta: some View {
        VStack(spacing: 8) {
            HStack { Text(match.home).font(.title3.black()); Spacer(); Text(score).font(.title.black()); Spacer(); Text(match.away).font(.title3.black()) }
            Text("\(SDDate.text(match.kickoff, includeTime: true)) · \(match.league)").font(.caption).foregroundStyle(SDTheme.muted)
            Text(match.statusText).font(.caption.bold()).foregroundStyle(SDTheme.muted)
        }.padding(.horizontal, 4)
    }

    private var matchCenter: some View {
        VStack(alignment: .leading, spacing: 14) {
            if match.venue != nil || match.referee != nil || match.attendance != nil {
                Text("Maç Bilgileri").font(.title3.bold())
                SDCard {
                    VStack(alignment: .leading, spacing: 9) {
                        if let venue = match.venue { Label(venue, systemImage: "sportscourt") }
                        if let referee = match.referee { Label(referee, systemImage: "person.fill") }
                        if let attendance = match.attendance { Label("\(attendance.formatted()) seyirci", systemImage: "person.3.fill") }
                    }.font(.subheadline)
                }
            }
            if !match.events.isEmpty {
                Text("Maçın Olayları").font(.title3.bold())
                SDCard {
                    VStack(spacing: 11) {
                        ForEach(match.events) { event in
                            HStack(alignment: .top, spacing: 12) {
                                Text("\(event.minute)’").font(.headline.monospacedDigit()).foregroundStyle(SDTheme.accent).frame(width: 42, alignment: .leading)
                                Image(systemName: eventIcon(event.type)).frame(width: 22)
                                VStack(alignment: .leading, spacing: 2) { Text(event.player ?? event.team).font(.subheadline.bold()); Text(event.detail ?? event.type).font(.caption).foregroundStyle(SDTheme.muted) }
                                Spacer()
                            }
                        }
                    }
                }
            }
            if !match.statistics.isEmpty {
                Text("Maç İstatistikleri").font(.title3.bold())
                SDCard {
                    VStack(spacing: 13) {
                        ForEach(match.statistics, id: \.name) { item in
                            VStack(spacing: 4) { HStack { Text(item.home).font(.subheadline.bold()); Spacer(); Text(item.name).font(.caption).foregroundStyle(SDTheme.muted); Spacer(); Text(item.away).font(.subheadline.bold()) }; Divider().overlay(Color.white.opacity(0.08)) }
                        }
                    }
                }
            }
            if !match.playerRatings.isEmpty {
                Text("Oyuncu Puanları").font(.title3.bold())
                SDCard {
                    VStack(spacing: 10) {
                        ForEach(match.playerRatings.sorted { ($0.rating ?? 0) > ($1.rating ?? 0) }) { row in
                            NavigationLink { PlayerDetailView(player: row.player) } label: {
                                HStack { VStack(alignment: .leading) { Text(row.player).font(.subheadline.bold()); Text(row.team).font(.caption2).foregroundStyle(SDTheme.muted) }; Spacer(); Text(row.rating.map { String(format: "%.1f", $0) } ?? "—").font(.headline.monospacedDigit()) }
                            }.buttonStyle(.plain)
                        }
                    }
                }
            }
            if match.events.isEmpty && match.statistics.isEmpty && match.playerRatings.isEmpty {
                SDCard { Label("Ayrıntılı olay, istatistik ve oyuncu puanı verisi henüz bu maç için sağlanmadı.", systemImage: "chart.xyaxis.line").font(.subheadline).foregroundStyle(SDTheme.muted) }
            }
        }
    }

    private func eventIcon(_ type: String) -> String {
        let value = type.lowercased()
        if value.contains("goal") || value.contains("gol") { return "soccerball" }
        if value.contains("card") || value.contains("kart") { return "rectangle.fill" }
        if value.contains("var") || value.contains("penalt") { return "video.fill" }
        return "circle.fill"
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

    private var score: String { match.scoreText }
}
