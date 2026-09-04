import SwiftUI

struct CommentatorsView: View {
    @EnvironmentObject var store: AppStore
    @State private var search = ""
    @State private var selectedFilter = "Tümü"
    private let filters = ["Tümü", "Aktif", "Yazar", "TV", "Podcast"]

    private var rows: [Commentator] {
        let all = store.payload?.commentators ?? []
        let searched = search.isEmpty ? all : all.filter { $0.name.localizedCaseInsensitiveContains(search) || $0.primarySource.localizedCaseInsensitiveContains(search) }
        return searched.sorted { store.statements(for: $0.id).count > store.statements(for: $1.id).count }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 14) {
                HStack { Text("Yorumcular").font(.largeTitle.black()); Spacer(); Image(systemName: "magnifyingglass").font(.title3) }
                searchBox
                filterBar
                ForEach(rows) { c in
                    NavigationLink { CommentatorProfileView(commentator: c) } label: {
                        HStack(spacing: 12) {
                            AvatarView(text: c.avatar, size: 48)
                            VStack(alignment: .leading, spacing: 4) {
                                Text(c.name).font(.headline)
                                let count = store.statements(for: c.id).count
                                Text("\(count) yorum · \(c.primarySource)").font(.caption).foregroundStyle(SDTheme.muted)
                            }
                            Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
                        }
                        .padding(.vertical, 10)
                        .overlay(alignment: .bottom) { Rectangle().fill(SDTheme.line).frame(height: 1) }
                    }.buttonStyle(.plain)
                }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
    }

    private var searchBox: some View {
        HStack(spacing: 10) { Image(systemName: "magnifyingglass").foregroundStyle(SDTheme.muted); TextField("Yorumcu ara...", text: $search) }
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
