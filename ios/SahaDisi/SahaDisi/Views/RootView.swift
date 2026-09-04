import SwiftUI
import Combine

struct RootView: View {
    @EnvironmentObject var store: AppStore
    private let refreshTimer = Timer.publish(every: 900, on: .main, in: .common).autoconnect()
    var body: some View {
        Group {
            if store.isLoading {
                ZStack {
                    SDTheme.background.ignoresSafeArea()
                    VStack(spacing: 18) { SDLogo(); Text("Futbolun tüm sesleri, tek yerde.").font(.caption).foregroundStyle(SDTheme.muted); ProgressView().tint(SDTheme.accent) }
                }
            } else if store.payload != nil { MainTabsView() }
            else { ContentUnavailableView("Veri yüklenemedi", systemImage: "wifi.exclamationmark", description: Text(store.errorText ?? "Bilinmeyen hata")) }
        }
        .preferredColorScheme(.dark)
        .onReceive(refreshTimer) { _ in
            guard store.payload != nil, !store.isRefreshing else { return }
            Task { await store.refresh() }
        }
    }
}

struct MainTabsView: View {
    var body: some View {
        TabView {
            NavigationStack { HomeView() }.tabItem { Label("Ana Sayfa", systemImage: "house.fill") }
            NavigationStack { MatchesView() }.tabItem { Label("Maçlar", systemImage: "rectangle.grid.2x2.fill") }
            NavigationStack { ExploreView() }.tabItem { Label("Keşfet", systemImage: "magnifyingglass") }
            NavigationStack { CommentatorsView() }.tabItem { Label("Yorumcular", systemImage: "person.crop.circle") }
            NavigationStack { MoreView() }.tabItem { Label("Daha Fazla", systemImage: "ellipsis") }
        }
        .tint(SDTheme.accent)
        .toolbarBackground(SDTheme.background2, for: .tabBar)
    }
}

struct MoreView: View {
    @EnvironmentObject var store: AppStore
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                Text("Daha Fazla").font(.largeTitle.black()).padding(.bottom, 22)
                menu("Ayarlar", "gearshape")
                menu("Bildirimler", "bell")
                menu("Takip Ettiklerim", "heart")
                NavigationLink { DataStatusView() } label: { menu("Veri Kaynakları", "shippingbox", chevron: true) }.buttonStyle(.plain)
                menu("Hakkında", "info.circle")
                menu("Geri Bildirim", "rectangle.and.pencil.and.ellipsis")
                VStack(spacing: 10) {
                    SDLogo()
                    Text("v1.0.0").font(.caption2).foregroundStyle(SDTheme.muted2)
                    Text("Futbolun tüm sesleri, tek yerde.").font(.caption).foregroundStyle(SDTheme.muted)
                }.frame(maxWidth: .infinity).padding(.top, 70)
            }.padding(18)
        }.background(SDTheme.background)
    }
    private func menu(_ title: String, _ icon: String, chevron: Bool = true) -> some View {
        HStack(spacing: 14) { Image(systemName: icon).frame(width: 24); Text(title).font(.body.weight(.medium)); Spacer(); if chevron { Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2) } }
            .padding(.vertical, 17).overlay(alignment: .bottom) { Rectangle().fill(SDTheme.line).frame(height: 1) }
    }
}
