import SwiftUI

struct StatementDetailView: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let c = store.commentator(id: statement.commentator) {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 58, photoURL: c.photoURL)
                        Text(c.name).font(.headline)
                        Spacer()
                        Text(SDDate.text(statement.date, includeTime: true)).font(.caption).foregroundStyle(SDTheme.muted).lineLimit(1).minimumScaleFactor(0.72)
                    }
                }

                Text(statement.summary)
                    .font(.system(size: 24, weight: .semibold, design: .rounded))
                    .lineSpacing(6).fixedSize(horizontal: false, vertical: true)

                if let imageURL = statement.imageURL, let url = URL(string: imageURL) {
                    AsyncImage(url: url) { phase in
                        if case .success(let image) = phase {
                            image.resizable().scaledToFill()
                        } else {
                            Rectangle().fill(SDTheme.panel2)
                        }
                    }
                    .frame(height: 205).frame(maxWidth: .infinity).clipped()
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                }

                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) } }
                Divider().overlay(SDTheme.line)
                StatementSocialBar(statement: statement)
                Divider().overlay(SDTheme.line)

                if let url = URL(string: statement.url) {
                    Link(destination: url) {
                        Label("Kaynağı aç", systemImage: "arrow.up.right")
                            .font(.subheadline.bold()).foregroundStyle(SDTheme.accent)
                    }
                }
            }.padding(18)
        }.background(SDTheme.background)
    }
}
