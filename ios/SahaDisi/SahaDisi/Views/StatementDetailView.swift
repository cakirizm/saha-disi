import SwiftUI

struct StatementDetailView: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if let c = store.commentator(id: statement.commentator) {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 58, photoURL: c.photoURL)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(c.name).font(.headline)
                            Text(c.role).font(.caption).foregroundStyle(SDTheme.muted)
                            Text(statement.source).font(.caption2).foregroundStyle(SDTheme.muted2)
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 10) {
                    Text(statement.type == "prediction" ? "Ne söyledi?" : "Ana fikir").font(.caption.bold()).foregroundStyle(SDTheme.accent)
                    Text("“\(statement.summary)”").font(.system(size: 25, weight: .bold)).lineSpacing(5)
                }

                HStack { TagPill(text: statement.topic); if let team = statement.team { TagPill(text: team) } }

                SDCard {
                    VStack(alignment: .leading, spacing: 7) {
                        Text("Kısa özet").font(.headline)
                        Text(contextText).font(.subheadline).foregroundStyle(SDTheme.muted)
                    }
                }

                HStack {
                    label("İddia", "\(statement.strength)/10")
                    label("Güven", "%\(statement.confidence)")
                    label("Tarih", SDDate.text(statement.date))
                }

                if let url = URL(string: statement.url) {
                    Link(destination: url) {
                        Label("Orijinal kaynağa git", systemImage: "arrow.up.right.square.fill")
                            .font(.headline).frame(maxWidth: .infinity).padding(15)
                            .background(SDTheme.accent).foregroundStyle(.black).clipShape(RoundedRectangle(cornerRadius: 14))
                    }
                }
                Text("Saha Dışı görüşü kısa ve anlaşılır biçimde gösterir; tam bağlam için orijinal kaynak açılabilir.").font(.caption).foregroundStyle(SDTheme.muted)
            }.padding(18)
        }.background(SDTheme.background)
    }

    private var contextText: String {
        let who = store.commentator(id: statement.commentator)?.name ?? "Yorumcu"
        if let team = statement.team, !statement.players.isEmpty { return "\(who), \(team) ve \(statement.players.joined(separator: ", ")) hakkında bu değerlendirmeyi yaptı." }
        if let team = statement.team { return "\(who), \(team) hakkında bu değerlendirmeyi yaptı." }
        if !statement.players.isEmpty { return "\(who), \(statement.players.joined(separator: ", ")) hakkında konuştu." }
        return "\(who), futbol gündemindeki bu başlık hakkında değerlendirme yaptı. Detay ve bağlam için kaynağı açabilirsin."
    }

    private func label(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) { Text(value).bold().lineLimit(2).minimumScaleFactor(0.72); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity, alignment: .leading)
    }
}
