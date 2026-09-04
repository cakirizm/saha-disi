import SwiftUI

struct TeamDetailView: View {
    @EnvironmentObject var store: AppStore
    let team: String

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 22) {
                Text(team).font(.largeTitle.weight(.black))
                Text("Kim en çok konuşuyor?").font(.title3.bold())
                ForEach(Array(store.commentatorRanking(for: team).enumerated()), id: \.offset) { index, row in
                    NavigationLink { CommentatorProfileView(commentator: row.0) } label: {
                        HStack(spacing: 12) {
                            Text("\(index + 1)").font(.title3.weight(.black)).foregroundStyle(SDTheme.accent).frame(width: 28)
                            AvatarView(text: row.0.avatar, size: 42)
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
}
