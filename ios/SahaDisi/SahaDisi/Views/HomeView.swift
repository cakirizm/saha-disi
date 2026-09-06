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
                latestFeed
                PublicationList(items: Array((store.payload?.publications ?? []).prefix(8)))
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
                LiveFootballMark()
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
                GeometryReader { geometry in
                    TabView(selection: $heroIndex) {
                        ForEach(Array(featuredMatches.enumerated()), id: \.element.id) { index, match in
                            NavigationLink { MatchDetailView(match: match) } label: {
                                matchHero(match).frame(width: max(0, geometry.size.width - 4))
                            }.buttonStyle(.plain).frame(width: geometry.size.width, height: 250).tag(index)
                        }
                    }.frame(width: geometry.size.width, height: 250)
                        .tabViewStyle(.page(indexDisplayMode: .never))
                        .clipped()
                }.frame(height: 250)
                .onChange(of: featuredMatches.map(\.id)) { _, _ in heroIndex = 0 }
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
        VStack(spacing: 18) {
            HStack {
                Text("SÜPER LİG").font(.caption2.bold()).tracking(1)
                Spacer()
                Text("\(match.week). Hafta").font(.caption)
            }.foregroundStyle(SDTheme.muted)
            HStack(alignment: .center, spacing: 12) {
                heroTeam(match.home, logo: match.homeLogoURL)
                VStack(spacing: 6) {
                    Text(match.scoreText).font(.title2.black()).monospacedDigit().lineLimit(1).minimumScaleFactor(0.8)
                    Text(match.statusText).font(.caption2).foregroundStyle(SDTheme.muted).multilineTextAlignment(.center)
                }.frame(width: 84)
                heroTeam(match.away, logo: match.awayLogoURL)
            }
            Text(SDDate.text(match.kickoff, includeTime: true))
                .font(.caption).foregroundStyle(SDTheme.muted).lineLimit(1).minimumScaleFactor(0.8)
        }.padding(18).frame(maxWidth: .infinity).frame(height: 240)
            .background(SDTheme.panel)
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .overlay(RoundedRectangle(cornerRadius: 20).stroke(SDTheme.line))
    }

    private func heroTeam(_ name: String, logo: String?) -> some View {
        VStack(spacing: 10) {
            TeamLogoView(name: name, urlString: logo, size: 56)
            Text(name).font(.subheadline.bold()).lineLimit(2)
                .multilineTextAlignment(.center).frame(height: 40, alignment: .top)
        }.frame(maxWidth: .infinity)
    }

    private func heroHeadline(_ m: Match) -> String {
        guard let hs = m.homeScore, let as_ = m.awayScore else { return "\(m.home) - \(m.away)" }
        if hs == as_ { return "\(m.home) ile \(m.away) puanları paylaştı" }
        return "\(hs > as_ ? m.home : m.away) 3 puanı aldı"
    }
    private func heroSubline(_ m: Match) -> String {
        let count = store.statements(matchID: m.id).count
        let scoreText = m.scoreText
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

    private var latestFeed: some View {
        LazyVStack(alignment: .leading, spacing: 28) {
            VStack(alignment: .leading, spacing: 5) {
                Text("Gündemdeki Yorumcular").font(.title3.bold())
                Text("Son 7 günde akışta en çok yorumu bulunan kişiler")
                    .font(.caption).foregroundStyle(SDTheme.muted)
            }
            let sections = store.commentatorFeedSections
            if sections.isEmpty {
                SDCard { Text("Kaynaklı yorumlar geldikçe burada görünecek.").font(.subheadline).foregroundStyle(SDTheme.muted) }
            }
            ForEach(sections) { section in
                CommentatorCarousel(section: section)
            }
        }
    }

    private var hotClaims: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("En İddialı Sözler", trailing: "Kaydır")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 12) {
                    ForEach(store.hotStatements.prefix(8)) { s in
                        NavigationLink { StatementDetailView(statement: s) } label: {
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
            SDCard { VStack(spacing: 7) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { TeamRankRow(rank: i + 1, item: item, maxCount: maxCount) }.buttonStyle(.plain) } } }
        }
    }

    private var activeCommentators: some View {
        VStack(alignment: .leading, spacing: 10) {
            header("Öne Çıkan Yorumcular", trailing: "\(store.payload?.commentators.count ?? 0) kişi")
            ForEach(store.rankedCommentators.prefix(6), id: \.0.id) { c, count in
                NavigationLink { CommentatorProfileView(commentator: c) } label: {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 46, photoURL: c.photoURL)
                        Text(c.name).font(.headline)
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
    private func score(_ m: Match) -> String { m.scoreText }
    private func header(_ title: String, trailing: String) -> some View { HStack { Text(title).font(.title3.bold()); Spacer(); Text(trailing).font(.caption).foregroundStyle(SDTheme.accent) } }
}

struct CommentatorCarousel: View {
    let section: CommentatorFeedSection
    @ScaledMetric(relativeTo: .body) private var cardHeight: CGFloat = 222

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .center, spacing: 10) {
                AvatarView(text: section.commentator.avatar, size: 40, photoURL: section.commentator.photoURL)
                VStack(alignment: .leading, spacing: 3) {
                    Text(section.commentator.name).font(.headline).lineLimit(2)
                    Text("Son 7 günde \(section.recentCount) yorum").font(.caption2).foregroundStyle(SDTheme.muted)
                }
                Spacer(minLength: 4)
                NavigationLink { CommentatorCommentsView(commentator: section.commentator) } label: {
                    Text("Tamamını gör").font(.caption.bold()).fixedSize(horizontal: true, vertical: false)
                        .foregroundStyle(SDTheme.accent).frame(minHeight: 44)
                }.buttonStyle(.plain)
            }
            ScrollView(.horizontal, showsIndicators: false) {
                LazyHStack(spacing: 12) {
                    ForEach(Array(section.statements.prefix(6).enumerated()), id: \.element.id) { index, statement in
                        NavigationLink { StatementDetailView(statement: statement) } label: {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    Text(SDDate.text(statement.date)).lineLimit(1)
                                    Spacer()
                                    Text("\(index + 1) / \(min(section.statements.count, 6))").monospacedDigit()
                                }.font(.caption2).foregroundStyle(SDTheme.muted)
                                Text("“\(statement.summary)”").font(.body.weight(.medium)).lineSpacing(4)
                                    .lineLimit(5).multilineTextAlignment(.leading)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                Spacer(minLength: 0)
                                HStack {
                                    Text(statement.source).lineLimit(1)
                                    Spacer(minLength: 8)
                                    Image(systemName: "arrow.up.right")
                                }.font(.caption).foregroundStyle(SDTheme.accent)
                            }.padding(16).frame(height: cardHeight, alignment: .topLeading)
                                .background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                                .overlay(RoundedRectangle(cornerRadius: 16).stroke(SDTheme.line))
                        }.buttonStyle(.plain).containerRelativeFrame(.horizontal)
                    }
                }.scrollTargetLayout()
            }.scrollTargetBehavior(.viewAligned)
        }
    }
}

struct CommentatorCommentsView: View {
    @EnvironmentObject var store: AppStore
    let commentator: Commentator
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                ForEach(store.statements(for: commentator.id)) { statement in
                    StatementTweetCard(statement: statement)
                }
            }.padding(16)
        }.background(SDTheme.background)
            .navigationTitle(commentator.name).navigationBarTitleDisplayMode(.inline)
            .refreshable { await store.refresh() }
    }
}

struct MatchArtwork: View {
    @EnvironmentObject var store: AppStore
    let match: Match
    var body: some View {
        ZStack {
            LinearGradient(colors: [Color.white.opacity(0.12), SDTheme.background2], startPoint: .topLeading, endPoint: .bottomTrailing)
            HStack(spacing: 0) {
                teamArtwork(store.artworkURL(for: match.home) ?? match.imageURL)
                teamArtwork(store.artworkURL(for: match.away) ?? match.imageURL)
            }
            LinearGradient(colors: [Color.black.opacity(0.12), Color.black.opacity(0.58)], startPoint: .top, endPoint: .bottom)
        }.clipped()
    }

    @ViewBuilder private func teamArtwork(_ value: String?) -> some View {
        if let value, let url = URL(string: value) {
            AsyncImage(url: url) { phase in
                if case .success(let image) = phase { image.resizable().scaledToFill() }
                else { artworkFallback }
            }.clipped()
        } else { artworkFallback }
    }
    private var artworkFallback: some View {
        ZStack {
            LinearGradient(colors: [SDTheme.panel2, SDTheme.background], startPoint: .top, endPoint: .bottom)
            Image(systemName: "soccerball").font(.system(size: 74, weight: .ultraLight)).foregroundStyle(Color.white.opacity(0.12))
        }
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
                HStack(spacing: 6) {
                    Text(c?.name ?? statement.commentator).font(.subheadline.bold())
                    Text("· \(statement.source)").font(.caption2).foregroundStyle(SDTheme.muted).lineLimit(1)
                    Spacer()
                    Text(SDDate.text(statement.date)).font(.caption2).foregroundStyle(SDTheme.muted2)
                }
                Text("“\(statement.summary)”").font(.subheadline).lineLimit(5)
                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) }; Spacer(); Text("%\(statement.confidence)").font(.caption2).foregroundStyle(SDTheme.muted) }
            }
        }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
    }
}

struct StatementTweetCard: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    var body: some View {
        let commentator = store.commentator(id: statement.commentator)
        return VStack(alignment: .leading, spacing: 14) {
            NavigationLink { StatementDetailView(statement: statement) } label: {
                VStack(alignment: .leading, spacing: 14) {
                    HStack(spacing: 10) {
                        AvatarView(text: commentator?.avatar ?? "?", size: 44, photoURL: commentator?.photoURL)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(commentator?.name ?? statement.commentator).font(.headline).lineLimit(2)
                            Text(statement.source).font(.caption2.weight(.semibold)).foregroundStyle(SDTheme.muted).lineLimit(1)
                        }
                        Spacer(minLength: 0)
                    }
                    HStack {
                        Text(SDDate.text(statement.date)).foregroundStyle(SDTheme.muted)
                        Spacer(minLength: 8)
                        Text(sentimentText(statement.sentiment)).foregroundStyle(sentimentColor(statement.sentiment))
                    }.font(.caption2).lineLimit(1)
                    Text("“\(statement.summary)”").font(.body.weight(.medium)).lineSpacing(4).fixedSize(horizontal: false, vertical: true)
                    ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 6) {
                        if statement.players.count == 1, let player = statement.players.first,
                           let photo = store.playerProfile(named: player)?.photoURL, let url = URL(string: photo) {
                            HStack(spacing: 5) {
                                AsyncImage(url: url) { phase in
                                    if case .success(let img) = phase { img.resizable().scaledToFill() }
                                    else { Color.white.opacity(0.06) }
                                }.frame(width: 22, height: 22).clipShape(Circle())
                                Text(player).font(.caption2.weight(.semibold))
                            }
                            .padding(.leading, 4).padding(.trailing, 9).padding(.vertical, 3)
                            .background(Color.white.opacity(0.06)).clipShape(Capsule())
                        }
                        TagPill(text: statement.topic)
                        if let team = statement.team { TagPill(text: team) }
                        if statement.type == "transfer" { TagPill(text: "Transfer iddiası") }
                    }
                    }
                }
            }.buttonStyle(.plain)
            Divider().overlay(SDTheme.line)
            VStack(alignment: .leading, spacing: 10) {
                StatementSocialBar(statement: statement)
                if let url = URL(string: statement.url), !statement.url.isEmpty {
                    Link(destination: url) {
                        HStack(spacing: 4) {
                            Text(statement.sourceActionTitle).font(.caption.bold())
                            Image(systemName: statement.sourceActionIcon).font(.caption2)
                        }.foregroundStyle(SDTheme.accent).frame(maxWidth: .infinity, alignment: .trailing)
                            .padding(.vertical, 6)
                    }
                }
            }
        }
        .padding(16)
        .background(SDTheme.panel)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(SDTheme.line))
    }
}

func sentimentText(_ value: String) -> String {
    value == "positive" ? "Olumlu" : value == "negative" ? "Eleştirel" : "Nötr"
}
func sentimentColor(_ value: String) -> Color {
    value == "positive" ? SDTheme.green : value == "negative" ? SDTheme.red : SDTheme.muted
}

/// Feed card standing in for several commentators who share the same stance.
/// Tapping opens the swipeable per-commentator breakdown.
struct StatementGroupCard: View {
    @EnvironmentObject var store: AppStore
    let group: StatementGroup
    private var shown: [Statement] { Array(group.statements.prefix(4)) }

    var body: some View {
        NavigationLink { StatementGroupDetailView(group: group) } label: {
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 10) {
                    ZStack(alignment: .leading) {
                        ForEach(Array(shown.enumerated()), id: \.element.id) { i, s in
                            let c = store.commentator(id: s.commentator)
                            AvatarView(text: c?.avatar ?? "?", size: 34, photoURL: c?.photoURL)
                                .overlay(Circle().stroke(SDTheme.panel, lineWidth: 2))
                                .offset(x: CGFloat(i) * 21)
                        }
                    }
                    .frame(width: CGFloat(shown.count - 1) * 21 + 34, height: 34, alignment: .leading)
                    Text("\(group.commentatorCount) yorumcu aynı görüşte")
                        .font(.subheadline.bold())
                    Spacer()
                    Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(SDTheme.muted)
                }
                Text("“\(group.lead.summary)”")
                    .font(.body.weight(.medium)).lineSpacing(4).lineLimit(4)
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 6) {
                    TagPill(text: group.topic)
                    if let team = group.team { TagPill(text: team) }
                    Spacer()
                    Text(sentimentText(group.sentiment))
                        .font(.caption2.weight(.bold)).foregroundStyle(sentimentColor(group.sentiment))
                }
            }
            .padding(14)
            .background(SDTheme.panel)
            .overlay(alignment: .leading) { Rectangle().fill(SDTheme.accent).frame(width: 3) }
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(SDTheme.line))
        }.buttonStyle(.plain)
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
            ForEach(Array(store.rankedTeams.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { HStack(spacing: 12) { Text("\(i+1)").foregroundStyle(SDTheme.muted).frame(width: 22); TeamLogoView(name: item.name, urlString: store.logoURL(for: item.name), size: 42); Text(item.name).font(.headline); Spacer(); Text("\(item.count) yorum").font(.caption).foregroundStyle(SDTheme.accent); Image(systemName: "chevron.right").font(.caption) }.padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14)) }.buttonStyle(.plain) }
        }.padding(16) }.background(SDTheme.background).navigationTitle("Takımlar").navigationBarTitleDisplayMode(.inline)
    }
}

private struct TeamRankRow: View {
    @EnvironmentObject var store: AppStore
    let rank: Int
    let item: RankedItem
    let maxCount: Int

    var body: some View {
        HStack(spacing: 10) {
            Text("\(rank)").font(.subheadline.bold()).foregroundStyle(SDTheme.muted).frame(width: 20)
            TeamLogoView(name: item.name, urlString: store.logoURL(for: item.name), size: 34)
            Text(item.name).font(.subheadline.weight(.semibold)).lineLimit(1).frame(width: 105, alignment: .leading)
            GeometryReader { proxy in
                Capsule().fill(Color.white.opacity(0.06)).overlay(alignment: .leading) {
                    Capsule().fill(SDTheme.accent).frame(width: max(8, proxy.size.width * CGFloat(item.count) / CGFloat(max(1, maxCount))))
                }
            }.frame(height: 6)
            Text("\(item.count)").font(.subheadline.bold()).frame(width: 28, alignment: .trailing)
        }.frame(height: 38)
    }
}
