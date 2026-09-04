import SwiftUI

struct HomeView: View {
    @EnvironmentObject var store: AppStore
    @State private var heroIndex = 0

    private var featuredMatches: [Match] {
        Array((store.payload?.matches ?? []).sorted { a, b in
            let ac = store.statements(matchID: a.id).count
            let bc = store.statements(matchID: b.id).count
            if ac != bc { return ac > bc }
            return a.kickoff > b.kickoff
        }.prefix(4))
    }
    private var recentMatches: [Match] {
        Array((store.payload?.matches ?? []).filter { $0.homeScore != nil }.sorted { $0.kickoff > $1.kickoff }.prefix(4))
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 18) {
                topNav
                agendaCarousel
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
            HStack {
                SDLogo()
                Spacer()
                NavigationLink { ExploreView() } label: { Image(systemName: "magnifyingglass").font(.title3).frame(width: 38, height: 38) }
                NavigationLink { MoreDetailView(title: "Bildirimler", icon: "bell") } label: { Image(systemName: "bell").font(.title3).frame(width: 38, height: 38) }
            }.buttonStyle(.plain).padding(.top, 10)

            HStack(spacing: 0) {
                connectedTab("Futbol", selected: true) { MatchesView() }
                connectedTab("Yorumcular", selected: false) { CommentatorsView() }
                connectedTab("Oyuncular", selected: false) { PlayerDirectoryView() }
                connectedTab("Takımlar", selected: false) { TeamDirectoryView() }
            }
            Rectangle().fill(SDTheme.line).frame(height: 1)
        }
    }

    private func connectedTab<Destination: View>(_ text: String, selected: Bool, @ViewBuilder destination: () -> Destination) -> some View {
        NavigationLink(destination: destination()) {
            VStack(spacing: 8) {
                Text(text).font(.caption.weight(selected ? .bold : .medium)).foregroundStyle(selected ? .white : SDTheme.muted).frame(maxWidth: .infinity)
                Capsule().fill(selected ? SDTheme.accent : .clear).frame(height: 2)
            }
        }.buttonStyle(.plain)
    }

    private var agendaCarousel: some View {
        VStack(spacing: 8) {
            if featuredMatches.isEmpty {
                SDCard { Text("Gündem verisi yükleniyor…").foregroundStyle(SDTheme.muted) }
            } else {
                TabView(selection: $heroIndex) {
                    ForEach(Array(featuredMatches.enumerated()), id: \.element.id) { index, match in
                        NavigationLink { MatchDetailView(match: match) } label: { matchHero(match) }.buttonStyle(.plain).tag(index)
                    }
                }.frame(height: 250).tabViewStyle(.page(indexDisplayMode: .never))
                HStack(spacing: 6) {
                    ForEach(featuredMatches.indices, id: \.self) { index in
                        Button { withAnimation { heroIndex = index } } label: {
                            Capsule().fill(index == heroIndex ? SDTheme.accent : Color.white.opacity(0.18)).frame(width: index == heroIndex ? 18 : 6, height: 6)
                        }.buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private func matchHero(_ match: Match) -> some View {
        ZStack(alignment: .bottomLeading) {
            MatchArtwork(match: match)
            LinearGradient(colors: [.clear, Color.black.opacity(0.90)], startPoint: .top, endPoint: .bottom)
            VStack(alignment: .leading, spacing: 9) {
                HStack { TagPill(text: "GÜNDEM", highlighted: true); Spacer(); Text("\(match.week). Hafta").font(.caption2.bold()).foregroundStyle(.white.opacity(0.8)) }
                Text(heroHeadline(match)).font(.system(size: 25, weight: .black, design: .rounded)).lineLimit(2)
                Text(heroSubline(match)).font(.subheadline).foregroundStyle(Color.white.opacity(0.82)).lineLimit(2)
                Text(SDDate.text(match.kickoff, includeTime: true)).font(.caption2).foregroundStyle(Color.white.opacity(0.58))
            }.padding(18)
        }.frame(height: 240).clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous)).overlay(RoundedRectangle(cornerRadius: 22).stroke(SDTheme.line))
    }

    private func heroHeadline(_ m: Match) -> String {
        guard let hs = m.homeScore, let as_ = m.awayScore else { return "\(m.home) - \(m.away)" }
        if hs == as_ { return "\(m.home) ile \(m.away) puanları paylaştı" }
        return "\(hs > as_ ? m.home : m.away) 3 puanı aldı"
    }
    private func heroSubline(_ m: Match) -> String {
        let count = store.statements(matchID: m.id).count
        let scoreText = (m.homeScore != nil && m.awayScore != nil) ? "\(m.homeScore!)-\(m.awayScore!)" : "vs"
        return "\(m.home) \(scoreText) \(m.away) · \(count) doğrulanmış yorum"
    }

    private var compactScores: some View {
        VStack(alignment: .leading, spacing: 8) {
            header("Son Maçlar", trailing: "TFF")
            ForEach(recentMatches, id: \.id) { match in
                NavigationLink { MatchDetailView(match: match) } label: {
                    HStack(spacing: 10) {
                        TeamLogoView(name: match.home, urlString: match.homeLogoURL, size: 36)
                        Text(match.home).font(.subheadline.weight(.semibold)).frame(maxWidth: .infinity, alignment: .leading)
                        Text(score(match)).font(.headline.black()).frame(width: 54)
                        Text(match.away).font(.subheadline.weight(.semibold)).frame(maxWidth: .infinity, alignment: .trailing)
                        TeamLogoView(name: match.away, urlString: match.awayLogoURL, size: 36)
                    }.padding(.horizontal, 12).padding(.vertical, 10).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 12))
                }.buttonStyle(.plain)
            }
        }
    }

    private var hotClaims: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En İddialı Sözler", trailing: "Kaydır")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.hotStatements.prefix(8)) { s in
                        NavigationLink(value: s) {
                            VStack(alignment: .leading, spacing: 10) {
                                let c = store.commentator(id: s.commentator)
                                HStack(spacing: 8) { AvatarView(text: c?.avatar ?? "?", size: 34, photoURL: c?.photoURL); Text(c?.name ?? s.commentator).font(.caption.bold()).lineLimit(1) }
                                Text("“\(s.summary)”").font(.subheadline.weight(.semibold)).lineLimit(4).frame(height: 74, alignment: .top)
                                HStack { outcomeBadge(s); Spacer(); Text(SDDate.text(s.date)).font(.caption2).foregroundStyle(SDTheme.muted2) }
                            }.padding(14).frame(width: 275, alignment: .leading).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                        }.buttonStyle(.plain)
                    }
                }
            }
        }
    }

    private var topPlayers: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En Çok Konuşulan Oyuncular", trailing: "Canlı")
            let rows = Array(store.rankedPlayers.prefix(5)); let maxCount = rows.first?.count ?? 1
            SDCard { VStack(spacing: 5) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { PlayerDetailView(player: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain) } } }
        }
    }

    private var topTeams: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En Çok Konuşulan Takımlar", trailing: "Canlı")
            let rows = Array(store.rankedTeams.prefix(5)); let maxCount = rows.first?.count ?? 1
            SDCard { VStack(spacing: 5) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain) } } }
        }
    }

    private var activeCommentators: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("Öne Çıkan Yorumcular", trailing: "\(store.payload?.commentators.count ?? 0) kişi")
            ForEach(store.rankedCommentators.prefix(6), id: \.0.id) { c, count in
                NavigationLink { CommentatorProfileView(commentator: c) } label: {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 46, photoURL: c.photoURL)
                        VStack(alignment: .leading, spacing: 2) { Text(c.name).font(.headline); Text(c.primarySource).font(.caption2).foregroundStyle(SDTheme.muted).lineLimit(1) }
                        Spacer(); Text("\(count) yorum").font(.caption.bold()).foregroundStyle(count == 0 ? SDTheme.muted2 : SDTheme.accent)
                        Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                    }.padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14))
                }.buttonStyle(.plain)
            }
        }
    }

    private func outcomeBadge(_ s: Statement) -> some View {
        let text = s.predictionOutcome == "correct" ? "DOĞRU" : (s.predictionOutcome == "wrong" ? "YANLIŞ" : "İDDİALI")
        let color = s.predictionOutcome == "correct" ? SDTheme.green : (s.predictionOutcome == "wrong" ? SDTheme.red : SDTheme.accent)
        return Text(text).font(.caption2.black()).padding(.horizontal, 7).padding(.vertical, 4).background(color.opacity(0.15)).foregroundStyle(color).clipShape(RoundedRectangle(cornerRadius: 5))
    }
    private func score(_ m: Match) -> String { if let h = m.homeScore, let a = m.awayScore { return "\(h) - \(a)" }; return "vs" }
    private func header(_ title: String, trailing: String) -> some View { HStack { Text(title).font(.title3.bold()); Spacer(); Text(trailing).font(.caption).foregroundStyle(SDTheme.accent) } }
}

struct MatchArtwork: View {
    let match: Match
    var body: some View {
        ZStack {
            LinearGradient(colors: [Color.white.opacity(0.12), SDTheme.background2], startPoint: .topLeading, endPoint: .bottomTrailing)
            if let imageURL = match.imageURL, let url = URL(string: imageURL) {
                AsyncImage(url: url) { phase in if case .success(let image) = phase { image.resizable().scaledToFill().opacity(0.40) } }
            }
            HStack(spacing: 24) {
                TeamLogoView(name: match.home, urlString: match.homeLogoURL, size: 82)
                Text("VS").font(.caption.black()).foregroundStyle(Color.white.opacity(0.45))
                TeamLogoView(name: match.away, urlString: match.awayLogoURL, size: 82)
            }
        }.clipped()
    }
}

struct MatchMiniArt: View {
    let match: Match
    var body: some View { HStack(spacing: -7) { TeamLogoView(name: match.home, urlString: match.homeLogoURL, size: 31); TeamLogoView(name: match.away, urlString: match.awayLogoURL, size: 31) }.frame(width: 48, height: 38) }
}

struct StatementRow: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            let c = store.commentator(id: statement.commentator)
            AvatarView(text: c?.avatar ?? "?", size: 42, photoURL: c?.photoURL)
            VStack(alignment: .leading, spacing: 7) {
                HStack { Text(c?.name ?? statement.commentator).font(.subheadline.bold()); Spacer(); Text(SDDate.text(statement.date)).font(.caption2).foregroundStyle(SDTheme.muted2) }
                Text(statement.summary).font(.subheadline).lineLimit(5)
                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) }; Spacer(); Text("%\(statement.confidence)").font(.caption2).foregroundStyle(SDTheme.muted) }
            }
        }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
    }
}

struct PlayerDirectoryView: View {
    @EnvironmentObject var store: AppStore
    var body: some View {
        ScrollView { LazyVStack(alignment: .leading, spacing: 12) {
            Text("Oyuncular").font(.largeTitle.black()); Text("Yorumlarda en çok geçen oyuncular").foregroundStyle(SDTheme.muted)
            ForEach(Array(store.rankedPlayers.enumerated()), id: \.element.id) { i, item in NavigationLink { PlayerDetailView(player: item.name) } label: { HStack { Text("\(i+1)").foregroundStyle(SDTheme.muted); Text(item.name).font(.headline); Spacer(); Text("\(item.count) yorum").font(.caption).foregroundStyle(SDTheme.accent); Image(systemName: "chevron.right").font(.caption) }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14)) }.buttonStyle(.plain) }
        }.padding(16) }.background(SDTheme.background).navigationTitle("Oyuncular").navigationBarTitleDisplayMode(.inline)
    }
}

struct TeamDirectoryView: View {
    @EnvironmentObject var store: AppStore
    var body: some View {
        ScrollView { LazyVStack(alignment: .leading, spacing: 12) {
            Text("Takımlar").font(.largeTitle.black()); Text("Yorumlarda öne çıkan takımlar").foregroundStyle(SDTheme.muted)
            ForEach(Array(store.rankedTeams.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { HStack { Text("\(i+1)").foregroundStyle(SDTheme.muted); Text(item.name).font(.headline); Spacer(); Text("\(item.count) yorum").font(.caption).foregroundStyle(SDTheme.accent); Image(systemName: "chevron.right").font(.caption) }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14)) }.buttonStyle(.plain) }
        }.padding(16) }.background(SDTheme.background).navigationTitle("Takımlar").navigationBarTitleDisplayMode(.inline)
    }
}
