import SwiftUI

struct ExploreView: View {
    @EnvironmentObject var store: AppStore
    @State private var search = ""
    @State private var selected = "Oyuncular"
    private let tabs = ["Oyuncular", "Takımlar", "Konular", "Trendler"]

    var filtered: [Statement] {
        guard !search.isEmpty else { return store.payload?.statements ?? [] }
        return (store.payload?.statements ?? []).filter {
            $0.summary.localizedCaseInsensitiveContains(search) ||
            ($0.team?.localizedCaseInsensitiveContains(search) ?? false) ||
            $0.players.contains(where: { $0.localizedCaseInsensitiveContains(search) }) ||
            (store.commentator(id: $0.commentator)?.name.localizedCaseInsensitiveContains(search) ?? false)
        }
    }

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                Text("Keşfet").font(.largeTitle.black())
                searchBox
                tabBar
                if !search.isEmpty { searchResults }
                else if selected == "Oyuncular" { playersSection }
                else if selected == "Takımlar" { teamsSection }
                else { trendSection }
            }.padding(16)
        }
        .background(SDTheme.background)
        .toolbar(.hidden, for: .navigationBar)
        .refreshable { await store.refresh() }
        .navigationDestination(for: Statement.self) { StatementDetailView(statement: $0) }
    }

    private var searchBox: some View {
        HStack { Image(systemName: "magnifyingglass").foregroundStyle(SDTheme.muted); TextField("Yorumcu, takım veya oyuncu ara", text: $search) }
            .padding(.horizontal, 14).frame(height: 44).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var tabBar: some View {
        HStack(spacing: 8) {
            ForEach(tabs, id: \.self) { tab in
                Button { selected = tab } label: {
                    Text(tab).font(.caption.bold()).padding(.horizontal, 12).padding(.vertical, 8)
                        .foregroundStyle(selected == tab ? Color.black : SDTheme.muted)
                        .background(selected == tab ? Color.white : SDTheme.panel)
                        .clipShape(Capsule())
                }.buttonStyle(.plain)
            }
        }
    }

    private var playersSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionHeader("En Çok Konuşulan Oyuncular", "Tümü")
            Text("Son veriler").font(.caption).foregroundStyle(SDTheme.muted)
            let rows = Array(store.rankedPlayers.prefix(10)); let maxCount = rows.first?.count ?? 1
            SDCard { VStack(spacing: 5) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { PlayerDetailView(player: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain) } } }
            teamsMini
            NavigationLink { DataStatusView() } label: {
                HStack { Image(systemName: "waveform.path.ecg"); Text("Canlı veri ve collector durumu").font(.subheadline.bold()); Spacer(); Image(systemName: "chevron.right").font(.caption) }
                    .padding(14).background(SDTheme.panel2).clipShape(RoundedRectangle(cornerRadius: 14))
            }.buttonStyle(.plain)
        }
    }

    private var teamsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionHeader("En Çok Konuşulan Takımlar", "Tümü")
            let rows = Array(store.rankedTeams.prefix(10)); let maxCount = rows.first?.count ?? 1
            SDCard { VStack(spacing: 5) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain) } } }
        }
    }

    private var trendSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            sectionHeader(selected == "Konular" ? "Gündem Konuları" : "Trend Sözler", "Canlı")
            ForEach(store.hotStatements.prefix(15)) { s in NavigationLink(value: s) { StatementRow(statement: s) }.buttonStyle(.plain) }
        }
    }

    private var teamsMini: some View {
        VStack(alignment: .leading, spacing: 10) {
            sectionHeader("En Çok Konuşulan Takımlar", "Tümü")
            let rows = Array(store.rankedTeams.prefix(5)); let maxCount = rows.first?.count ?? 1
            SDCard { VStack(spacing: 5) { ForEach(Array(rows.enumerated()), id: \.element.id) { i, item in NavigationLink { TeamDetailView(team: item.name) } label: { RankBar(rank: i + 1, name: item.name, count: item.count, maxCount: maxCount) }.buttonStyle(.plain) } } }
        }
    }

    private var searchResults: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Arama Sonuçları").font(.title3.bold())
            ForEach(filtered.prefix(30)) { s in NavigationLink(value: s) { StatementRow(statement: s) }.buttonStyle(.plain) }
        }
    }

    private func sectionHeader(_ title: String, _ trailing: String) -> some View { HStack { Text(title).font(.title3.bold()); Spacer(); Text(trailing).font(.caption).foregroundStyle(SDTheme.accent) } }
}
