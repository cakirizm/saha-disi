import SwiftUI

/// Breakdown of a cluster: each commentator who shares the stance gets their own
/// swipeable page ("Ahmet Çakar şunu dedi …"), navigated horizontally.
struct StatementGroupDetailView: View {
    let group: StatementGroup
    @State private var index = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 6) {
                    TagPill(text: group.topic)
                    if let team = group.team { TagPill(text: team) }
                    Spacer()
                    Text(sentimentText(group.sentiment))
                        .font(.caption2.weight(.bold)).foregroundStyle(sentimentColor(group.sentiment))
                }
                Text("\(group.commentatorCount) yorumcu aynı görüşte")
                    .font(.title3.bold())
                Text("Kaydırarak her yorumcunun sözünü ayrı ayrı gör · \(index + 1)/\(group.statements.count)")
                    .font(.caption).foregroundStyle(SDTheme.muted)
            }
            .padding(.horizontal, 18)
            .padding(.top, 8)

            TabView(selection: $index) {
                ForEach(Array(group.statements.enumerated()), id: \.element.id) { i, statement in
                    StatementGroupPage(statement: statement).tag(i)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .always))
            .indexViewStyle(.page(backgroundDisplayMode: .always))
        }
        .background(SDTheme.background)
        .navigationTitle("Ortak görüş")
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// One commentator's take inside a cluster: attribution, the verbatim quote and
/// a source-aware link to read/watch the full statement.
private struct StatementGroupPage: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let c = store.commentator(id: statement.commentator) {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 52, photoURL: c.photoURL)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(c.name).font(.headline)
                            Text(statement.source).font(.caption2.weight(.semibold)).foregroundStyle(SDTheme.muted)
                        }
                        Spacer()
                        Text(SDDate.text(statement.date)).font(.caption2).foregroundStyle(SDTheme.muted2)
                    }
                }

                HStack(alignment: .top, spacing: 12) {
                    Rectangle().fill(SDTheme.accent).frame(width: 3).clipShape(Capsule())
                    Text("“\(statement.summary)”")
                        .font(.system(size: 20, weight: .medium, design: .rounded))
                        .lineSpacing(6).fixedSize(horizontal: false, vertical: true)
                }

                if let url = URL(string: statement.url), !statement.url.isEmpty {
                    Link(destination: url) {
                        HStack(spacing: 10) {
                            Image(systemName: statement.sourceActionIcon)
                            Text(statement.sourceActionTitle).font(.subheadline.bold())
                            Spacer()
                            Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(SDTheme.muted)
                        }
                        .foregroundStyle(SDTheme.accent)
                        .padding(12)
                        .background(SDTheme.panel)
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(SDTheme.line))
                    }
                }

                Spacer(minLength: 24)
            }
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
