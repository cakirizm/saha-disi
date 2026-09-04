import SwiftUI

struct CommentatorsView: View {
    @EnvironmentObject var store: AppStore
    @State private var search = ""
    @State private var selectedFilter = "Tümü"
    private let filters = ["Tümü", "Aktif", "Yazar", "TV", "Podcast"]

    private var rows: [Commentator] {
        let all = store.payload?.commentators ?? []
        let searched = search.isEmpty ? all : all.filter {
            $0.name.localizedCaseInsensitiveContains(search) ||
            $0.primarySource.localizedCaseInsensitiveContains(search) ||
            $0.role.localizedCaseInsensitiveContains(search)
        }
        let filtered = searched.filter { commentator in
            switch selectedFilter {
            case "Aktif": return !store.statements(for: commentator.id).isEmpty
            case "Yazar": return matches(commentator, keywords: ["yazar", "writer", "column", "gazete"])
            case "TV": return matches(commentator, keywords: ["tv", "trt", "bein", "tivibu", "a spor", "beyaz", "yorumcu"])
            case "Podcast": return matches(commentator, keywords: ["podcast", "socrates", "vole", "343", "youtube", "digital"])
            default: return true
            }
        }
        return filtered.sorted { lhs, rhs in
            let left = store.statements(for: lhs.id).count
            let right = store.statements(for: rhs.id).count
            if left != right { return left > right }
            return lhs.name.localizedCompare(rhs.name) == .orderedAscending
        }
    }

    private func matches(_ commentator: Commentator, keywords: [String]) -> Bool {
        let haystack = "\(commentator.role) \(commentator.primarySource)".lowercased()
        return keywords.contains { haystack.contains($0) }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack {
                    Text("Yorumcular").font(.largeTitle.weight(.black))
                    Spacer()
                    Text("\(rows.count)").font(.caption.bold()).foregroundStyle(SDTheme.muted)
                }
                searchBox
                filterBar
                Text("En çok doğrulanmış yorumu bulunanlar önce gösterilir.")
                    .font(.caption2).foregroundStyle(SDTheme.muted2)
                if rows.isEmpty {
                    ContentUnavailableView("Sonuç bulunamadı", systemImage: "person.2.slash", description: Text("Arama veya filtreyi değiştirmeyi dene."))
                        .frame(maxWidth: .infinity).padding(.top, 48)
                } else {
                    ForEach(rows) { c in
                        let count = store.statements(for: c.id).count
                        NavigationLink { CommentatorProfileView(commentator: c) } label: {
                            HStack(spacing: 12) {
                                AvatarView(text: c.avatar, size: 50, photoURL: c.photoURL)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(c.name).font(.headline)
                                    Text(count == 0 ? "Henüz doğrulanmış yorum yok" : "\(count) yorum · \(c.primarySource)")
                                        .font(.caption).foregroundStyle(count == 0 ? SDTheme.muted2 : SDTheme.muted)
                                }
                                Spacer()
                                Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                            }
                            .padding(.vertical, 10)
                            .overlay(alignment: .bottom) { Rectangle().fill(SDTheme.line).frame(height: 1) }
                        }.buttonStyle(.plain)
                    }
                }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
    }

    private var searchBox: some View {
        HStack(spacing: 10) {
            Image(systemName: "magnifyingglass").foregroundStyle(SDTheme.muted)
            TextField("Yorumcu ara...", text: $search)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            if !search.isEmpty {
                Button { search = "" } label: { Image(systemName: "xmark.circle.fill").foregroundStyle(SDTheme.muted) }.buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 14).frame(height: 44).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var filterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(filters, id: \.self) { f in
                    Button { selectedFilter = f } label: {
                        Text(f).font(.caption.weight(.semibold)).padding(.horizontal, 13).padding(.vertical, 8)
                            .foregroundStyle(selectedFilter == f ? Color.black : SDTheme.muted)
                            .background(selectedFilter == f ? Color.white : SDTheme.panel)
                            .clipShape(Capsule())
                    }.buttonStyle(.plain)
                }
            }
        }
    }
}
