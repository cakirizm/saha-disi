import SwiftUI

struct StatementDetailView: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                if let c = store.commentator(id: statement.commentator) {
                    HStack(spacing: 12) { AvatarView(text: c.avatar, size: 54); VStack(alignment: .leading) { Text(c.name).font(.headline); Text(statement.source).font(.caption).foregroundStyle(SDTheme.muted) } }
                }
                Text("“\(statement.summary)”").font(.system(size: 28, weight: .bold)).lineSpacing(5)
                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) } }
                HStack { label("İddia", "\(statement.strength)/10"); label("Güven", "%\(statement.confidence)"); label("Tarih", statement.date) }
                if let url = URL(string: statement.url) {
                    Link(destination: url) { Label("Orijinal kaynağa git", systemImage: "arrow.up.right.square.fill").font(.headline).frame(maxWidth: .infinity).padding(15).background(SDTheme.accent).foregroundStyle(.black).clipShape(RoundedRectangle(cornerRadius: 14)) }
                }
                Text("Saha Dışı, kaynaktaki uzun içeriği kopyalamak yerine görüşü yapılandırılmış ve kısa bir özet olarak gösterir.").font(.caption).foregroundStyle(SDTheme.muted)
            }.padding(18)
        }.background(SDTheme.background)
    }

    private func label(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) { Text(value).bold(); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity, alignment: .leading)
    }
}
