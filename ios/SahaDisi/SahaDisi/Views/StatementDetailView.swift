import SwiftUI

struct StatementDetailView: View {
    @EnvironmentObject var store: AppStore
    let statement: Statement

    // Same subject (team + topic), other commentators' takes — the full spectrum.
    private var otherViews: [Statement] {
        guard let team = statement.team.map(store.canonicalTeam) else { return [] }
        return (store.payload?.statements ?? [])
            .filter { $0.id != statement.id && $0.topic == statement.topic && $0.team.map(store.canonicalTeam) == team }
            .sorted { $0.strength > $1.strength }
            .prefix(4).map { $0 }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let c = store.commentator(id: statement.commentator) {
                    HStack(spacing: 12) {
                        AvatarView(text: c.avatar, size: 58, photoURL: c.photoURL)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(c.name).font(.headline)
                            Text(statement.source).font(.caption2.weight(.semibold)).foregroundStyle(SDTheme.muted)
                        }
                        Spacer()
                        Text(SDDate.text(statement.date, includeTime: true)).font(.caption).foregroundStyle(SDTheme.muted).lineLimit(1).minimumScaleFactor(0.72)
                    }
                }

                // Söz, haber başlığı değil; yorumcunun birebir sözü. Tırnaklı alıntı bloğu.
                HStack(alignment: .top, spacing: 12) {
                    Rectangle().fill(SDTheme.accent).frame(width: 3).clipShape(Capsule())
                    Text("“\(statement.summary)”")
                        .font(.system(size: 21, weight: .medium, design: .rounded))
                        .lineSpacing(6).fixedSize(horizontal: false, vertical: true)
                }

                if let imageURL = store.commentator(id: statement.commentator)?.photoURL, let url = URL(string: imageURL) {
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
                if statement.type == "transfer" {
                    Text("Muhabirin aktarımıdır. Kulübün resmî duyurusu olmadan kesinleşmiş transfer sayılmaz.")
                        .font(.caption).foregroundStyle(SDTheme.muted)
                }
                Divider().overlay(SDTheme.line)
                StatementSocialBar(statement: statement)
                Divider().overlay(SDTheme.line)

                if let url = URL(string: statement.url), !statement.url.isEmpty {
                    Link(destination: url) {
                        HStack(spacing: 12) {
                            Image(systemName: statement.sourceActionIcon).font(.title3)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(statement.sourceActionTitle).font(.subheadline.bold())
                                Text(statement.sourceActionHint).font(.caption2).foregroundStyle(SDTheme.muted)
                            }
                            Spacer()
                            Image(systemName: "chevron.right").font(.caption.bold()).foregroundStyle(SDTheme.muted)
                        }
                        .foregroundStyle(SDTheme.accent)
                        .padding(14)
                        .background(SDTheme.panel)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(SDTheme.line))
                    }
                }

                if !otherViews.isEmpty {
                    Divider().overlay(SDTheme.line)
                    Text("Aynı konuda diğer görüşler").font(.headline)
                    ForEach(otherViews) { s in
                        NavigationLink { StatementDetailView(statement: s) } label: { StatementRow(statement: s) }.buttonStyle(.plain)
                    }
                }
            }.padding(18)
        }.background(SDTheme.background)
    }
}
