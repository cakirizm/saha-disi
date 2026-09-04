import SwiftUI

struct TeamDetailView: View {
    @EnvironmentObject var store: AppStore
    @StateObject private var notifications = NotificationService.shared
    let team: String

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 22) {
                HStack {
                    Text(team).font(.largeTitle.weight(.black))
                    Spacer()
                    notificationMenu
                }
                Text("Kim en çok konuşuyor?").font(.title3.bold())
                ForEach(Array(store.commentatorRanking(for: team).enumerated()), id: \.offset) { index, row in
                    NavigationLink { CommentatorProfileView(commentator: row.0, teamFilter: team) } label: {
                        HStack(spacing: 12) {
                            Text("\(index + 1)").font(.title3.weight(.black)).foregroundStyle(SDTheme.accent).frame(width: 28)
                            AvatarView(text: row.0.avatar, size: 42, photoURL: row.0.photoURL)
                            Text(row.0.name).font(.headline)
                            Spacer(); Text("\(row.1)").foregroundStyle(SDTheme.muted)
                        }.padding(12).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 15))
                    }.buttonStyle(.plain)
                }
                Text("En iddialı sözler").font(.title3.bold())
                ForEach(store.statements(team: team).sorted(by: { $0.strength > $1.strength })) { s in
                    NavigationLink(value: s) { StatementRow(statement: s) }.buttonStyle(.plain)
                }
            }.padding(16)
        }.background(SDTheme.background)
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var notificationMenu: some View {
        Menu {
            Button {
                Task { await notifications.toggleTeam(team) }
            } label: {
                Label(notifications.isTeamEnabled(team) ? "Takım bildirimini kapat" : "\(team) bildirimlerini aç", systemImage: notifications.isTeamEnabled(team) ? "bell.slash" : "bell")
            }
            Button {
                Task { await notifications.setAll(!notifications.allEnabled) }
            } label: {
                Label(notifications.allEnabled ? "Tüm bildirimleri kapat" : "Tüm bildirimleri aç", systemImage: notifications.allEnabled ? "bell.slash.fill" : "bell.badge")
            }
        } label: {
            Image(systemName: notifications.isTeamEnabled(team) || notifications.allEnabled ? "bell.fill" : "bell")
                .font(.headline).frame(width: 42, height: 42).background(SDTheme.panel).clipShape(Circle())
        }
    }
}
