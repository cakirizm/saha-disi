import SwiftUI

struct TeamDetailView: View {
    @EnvironmentObject var store: AppStore
    @StateObject private var notifications = NotificationService.shared
    let team: String

    private var teamLogoURL: String? {
        for match in store.payload?.matches ?? [] {
            if match.home == team { return match.homeLogoURL }
            if match.away == team { return match.awayLogoURL }
        }
        return nil
    }

    private var statements: [Statement] { store.statements(team: team) }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 22) {
                HStack(spacing: 14) {
                    TeamLogoView(name: team, urlString: teamLogoURL, size: 66)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(team).font(.largeTitle.weight(.black))
                        Text("Bu takım hakkında doğrulanmış yorumlar").font(.caption).foregroundStyle(SDTheme.muted)
                    }
                    Spacer(); notificationMenu
                }

                if !store.commentatorRanking(for: team).isEmpty {
                    Text("En Çok Konuşanlar").font(.title3.bold())
                    ForEach(Array(store.commentatorRanking(for: team).prefix(6).enumerated()), id: \.offset) { index, row in
                        NavigationLink { CommentatorProfileView(commentator: row.0, teamFilter: team) } label: {
                            HStack(spacing: 12) {
                                Text("\(index + 1)").font(.title3.weight(.black)).foregroundStyle(SDTheme.accent).frame(width: 28)
                                AvatarView(text: row.0.avatar, size: 42, photoURL: row.0.photoURL)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(row.0.name).font(.headline)
                                    Text("\(row.1) doğrulanmış yorum").font(.caption2).foregroundStyle(SDTheme.muted)
                                }
                                Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                            }.padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
                        }.buttonStyle(.plain)
                    }
                }

                Text("Hakkında Söylenenler").font(.title3.bold())
                if statements.isEmpty {
                    SDCard { Text("Bu takım için henüz doğrulanmış doğrudan yorum yok.").foregroundStyle(SDTheme.muted) }
                } else {
                    ForEach(statements) { s in
                        NavigationLink(value: s) {
                            let c = store.commentator(id: s.commentator)
                            VStack(alignment: .leading, spacing: 10) {
                                HStack(spacing: 10) {
                                    AvatarView(text: c?.avatar ?? "?", size: 42, photoURL: c?.photoURL)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(c?.name ?? s.commentator).font(.headline)
                                        Text("\(SDDate.text(s.date)) · \(s.source)").font(.caption2).foregroundStyle(SDTheme.muted)
                                    }
                                    Spacer(); Image(systemName: "chevron.right").foregroundStyle(SDTheme.accent)
                                }
                                Text("“\(s.summary)”").font(.subheadline.weight(.semibold)).lineLimit(6).multilineTextAlignment(.leading)
                                HStack {
                                    TagPill(text: s.topic)
                                    if !s.players.isEmpty { TagPill(text: s.players.prefix(2).joined(separator: ", ")) }
                                    Spacer(); Text("Yorumu aç").font(.caption.bold()).foregroundStyle(SDTheme.accent)
                                }
                            }.padding(14).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 16))
                        }.buttonStyle(.plain)
                    }
                }
            }.padding(16)
        }.background(SDTheme.background)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var notificationMenu: some View {
        Menu {
            Button { Task { await notifications.toggleTeam(team) } } label: {
                Label(notifications.isTeamEnabled(team) ? "Takım bildirimini kapat" : "\(team) bildirimlerini aç", systemImage: notifications.isTeamEnabled(team) ? "bell.slash" : "bell")
            }
            Button { Task { await notifications.setAll(!notifications.allEnabled) } } label: {
                Label(notifications.allEnabled ? "Tüm bildirimleri kapat" : "Tüm bildirimleri aç", systemImage: notifications.allEnabled ? "bell.slash.fill" : "bell.badge")
            }
        } label: {
            Image(systemName: notifications.isTeamEnabled(team) || notifications.allEnabled ? "bell.fill" : "bell")
                .font(.headline).frame(width: 42, height: 42).background(SDTheme.panel).clipShape(Circle())
        }
    }
}
