import SwiftUI

struct HomeView: View {
    @EnvironmentObject var store: AppStore
    private var featuredMatch: Match? {
        (store.payload?.matches ?? []).sorted { $0.kickoff > $1.kickoff }.first { !$0.home.contains("Gençlerbirliği") }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                topNav
                if let match = featuredMatch { matchHero(match) }
                compactScores
                hotClaims
                topPlayers
                topTeams
                activeCommentators
            }.padding(.horizontal, 16).padding(.bottom, 24)
        }
        .background(SDTheme.background)
        .refreshable { await store.refresh() }
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
        .toolbar(.hidden, for: .navigationBar)
    }

    private var topNav: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack { SDLogo(); Spacer(); Image(systemName: "magnifyingglass").font(.title3); Image(systemName: "bell").font(.title3).padding(.leading, 10) }
                .padding(.top, 10)
            HStack(spacing: 24) {
                topTab("Futbol", true); topTab("Yorumcular", false); topTab("Oyuncular", false); topTab("Takımlar", false)
            }
            Rectangle().fill(SDTheme.line).frame(height: 1)
        }
    }

    private func topTab(_ text: String, _ selected: Bool) -> some View {
        VStack(spacing: 8) {
            Text(text).font(.caption.weight(selected ? .bold : .medium)).foregroundStyle(selected ? .white : SDTheme.muted)
            Capsule().fill(selected ? SDTheme.accent : .clear).frame(height: 2)
        }
    }

    private func matchHero(_ match: Match) -> some View {
        NavigationLink { MatchDetailView(match: match) } label: {
            ZStack(alignment: .bottomLeading) {
                LinearGradient(colors: [Color(red: 0.06, green: 0.13, blue: 0.17), Color.black.opacity(0.95)], startPoint: .top, endPoint: .bottom)
                VStack(alignment: .leading, spacing: 12) {
                    TagPill(text: "GÜNDEM", highlighted: true)
                    Text(heroHeadline(match)).font(.system(size: 27, weight: .black, design: .rounded)).lineLimit(2)
                    Text(heroSubline(match)).font(.subheadline).foregroundStyle(Color.white.opacity(0.82)).lineLimit(2)
                    HStack(spacing: 5) { Circle().fill(SDTheme.accent).frame(width: 5, height: 5); Circle().fill(Color.white.opacity(0.25)).frame(width: 5, height: 5); Circle().fill(Color.white.opacity(0.25)).frame(width: 5, height: 5) }
                }.padding(18)
            }
            .frame(height: 240)
            .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 22).stroke(SDTheme.line))
        }.buttonStyle(.plain)
    }

    private func heroHeadline(_ m: Match) -> String {
        guard let hs = m.homeScore, let as_ = m.awayScore else { return "\(m.home) - \(m.away)" }
        let winner = hs == as_ ? "Beraberlik" : (hs > as_ ? m.home : m.away)
        return hs == as_ ? "\(m.home) ile \(m.away) puanları paylaştı" : "\(winner) 3 puanı aldı"
    }
    private func heroSubline(_ m: Match) -> String {
        let count = store.statements(matchID: m.id).count
        return "\(m.home) \(m.homeScore ?? 0)-\(m.awayScore ?? 0) \(m.away) · \(count) doğrulanmış yorum"
    }

    private var compactScores: some View {
        VStack(spacing: 7) {
            ForEach(Array((store.payload?.matches ?? []).sorted { $0.kickoff > $1.kickoff }.prefix(3))) { match in
                NavigationLink { MatchDetailView(match: match) } label: {
                    HStack {
                        Text(match.home).font(.subheadline.weight(.semibold)).frame(maxWidth: .infinity, alignment: .leading)
                        Text(score(match)).font(.headline.black()).frame(width: 62)
                        Text(match.away).font(.subheadline.weight(.semibold)).frame(maxWidth: .infinity, alignment: .trailing)
                    }.padding(.horizontal, 14).padding(.vertical, 12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 12))
                }.buttonStyle(.plain)
            }
        }
    }

    private var hotClaims: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En İddialı Sözler", trailing: "Tümü")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.hotStatements.prefix(5)) { s in
                        NavigationLink(value: s) {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack(spacing: 8) { AvatarView(text: store.commentator(id: s.commentator)?.avatar ?? "?", size: 32); Text(store.commentator(id: s.commentator)?.name ?? s.commentator).font(.caption.bold()).lineLimit(1) }
                                Text("“\(s.summary)”").font(.subheadline.weight(.semibold)).lineLimit(3).frame(height: 58, alignment: .top)
                                HStack { outcomeBadge(s); Spacer(); Text(s.date).font(.caption2).foregroundStyle(SDTheme.muted2) }
                            }.padding(14).frame(width: 260, alignment: .leading).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                        }.buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var topPlayers: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En Çok Konuşulan Oyuncular", trailing: "Son veriler")
            SDCard {
                VStack(spacing: 5) {
                    let rows = Array(store.rankedPlayers.prefix(5))
                    let maxCount = rows.first?.count ?? 1
                    ForEach(Array(rows.enumerated()), id: \.element.id) { index, item in
                        NavigationLink { PlayerDetailView(player: item.name) } label: { RankBar(rank: index + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var topTeams: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En Çok Konuşulan Takımlar", trailing: "Tümü")
            SDCard {
                VStack(spacing: 5) {
                    let rows = Array(store.rankedTeams.prefix(5)); let maxCount = rows.first?.count ?? 1
                    ForEach(Array(rows.enumerated()), id: \.element.id) { index, item in
                        NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: index + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var activeCommentators: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("Öne Çıkan Yorumcular", trailing: "27 yorumcu")
            ForEach(store.rankedCommentators.prefix(5), id: \.0.id) { c, count in
                NavigationLink { CommentatorProfileView(commentator: c) } label: {
                    HStack(spacing: 12) { AvatarView(text: c.avatar, size: 44); VStack(alignment: .leading, spacing: 2) { Text(c.name).font(.headline); Text(c.primarySource).font(.caption2).foregroundStyle(SDTheme.muted) }; Spacer(); Text("\(count) yorum").font(.caption.bold()).foregroundStyle(SDTheme.accent); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2) }
                        .padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14))
                }.buttonStyle(.plain)
            }
        }
    }

    private func outcomeBadge(_ s: Statement) -> some View {
        let text: String = s.predictionOutcome == "correct" ? "DOĞRU" : (s.predictionOutcome == "wrong" ? "YANLIŞ" : "İDDİALI")
        let color: Color = s.predictionOutcome == "correct" ? SDTheme.green : (s.predictionOutcome == "wrong" ? SDTheme.red : SDTheme.accent)
        return Text(text).font(.caption2.black()).padding(.horizontal, 7).padding(.vertical, 4).background(color.opacity(0.15)).foregroundStyle(color).clipShape(RoundedRectangle(cornerRadius: 5))
    }
    private func score(_ m: Match) -> String { if let h = m.homeScore, let a = m.awayScore { return "\(h) - \(a)" }; return "vs" }
    private func header(_ title: String, trailing: String) -> some View { HStack { Text(title).font(.title3.bold()); Spacer(); Text(trailing).font(.caption).foregroundStyle(SDTheme.accent) } }
}

struct StatementRow: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            AvatarView(text: store.commentator(id: statement.commentator)?.avatar ?? "?", size: 42)
            VStack(alignment: .leading, spacing: 7) {
                HStack { Text(store.commentator(id: statement.commentator)?.name ?? statement.commentator).font(.subheadline.bold()); Spacer(); Text(statement.date).font(.caption2).foregroundStyle(SDTheme.muted2) }
                Text(statement.summary).font(.subheadline).lineLimit(4)
                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) }; Spacer(); Text("%\(statement.confidence)").font(.caption2).foregroundStyle(SDTheme.muted) }
            }
        }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
    }
}
