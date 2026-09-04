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
                NavigationLink { MoreDetailView(title: "Ayarlar", icon: "gearshape") } label: { menu("Ayarlar", "gearshape") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Bildirimler", icon: "bell") } label: { menu("Bildirimler", "bell") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Takip Ettiklerim", icon: "heart") } label: { menu("Takip Ettiklerim", "heart") }.buttonStyle(.plain)
                NavigationLink { DataStatusView() } label: { menu("Veri Kaynakları", "shippingbox") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Hakkında", icon: "info.circle") } label: { menu("Hakkında", "info.circle") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Geri Bildirim", icon: "rectangle.and.pencil.and.ellipsis") } label: { menu("Geri Bildirim", "rectangle.and.pencil.and.ellipsis") }.buttonStyle(.plain)
                VStack(spacing: 10) {
                    SDLogo()
                    Text("v1.0.0").font(.caption2).foregroundStyle(SDTheme.muted2)
                    Text("Futbol sahada oynanır. Burada konuşulur.").font(.caption).foregroundStyle(SDTheme.muted)
                    if let last = store.lastRefreshAt { Text("Son uygulama yenilemesi: \(last.formatted(date: .omitted, time: .shortened))").font(.caption2).foregroundStyle(SDTheme.muted2) }
                }.frame(maxWidth: .infinity).padding(.top, 60)
            }.padding(18)
        }.background(SDTheme.background)
    }

    private func menu(_ title: String, _ icon: String) -> some View {
        HStack(spacing: 14) {
            Image(systemName: icon).frame(width: 24)
            Text(title).font(.body.weight(.medium))
            Spacer()
            Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2)
        }
        .padding(.vertical, 17)
        .overlay(alignment: .bottom) { Rectangle().fill(SDTheme.line).frame(height: 1) }
    }
}

struct MoreDetailView: View {
    @EnvironmentObject var store: AppStore
    let title: String
    let icon: String
    @State private var notificationsEnabled = true
    @State private var liveDataEnabled = true

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 12) {
                    Image(systemName: icon).font(.title2).frame(width: 46, height: 46).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 13))
                    Text(title).font(.largeTitle.black())
                }

                if title == "Ayarlar" {
                    SDCard { Toggle("Canlı veri yenileme", isOn: $liveDataEnabled); Divider(); Toggle("Bildirimler", isOn: $notificationsEnabled) }
                } else if title == "Bildirimler" {
                    SDCard { VStack(alignment: .leading, spacing: 10) { Text("Bildirim tercihleri").font(.headline); Toggle("Yeni güçlü yorumlar", isOn: $notificationsEnabled); Text("Bildirim altyapısı etkinleştirildiğinde bu tercih kullanılacak.").font(.caption).foregroundStyle(SDTheme.muted) } }
                } else if title == "Takip Ettiklerim" {
                    SDCard { Text("Takip ettiğin yorumcular burada listelenecek. Yorumcu profillerindeki Takip Et düğmesini kullanabilirsin.").foregroundStyle(SDTheme.muted) }
                } else if title == "Hakkında" {
                    SDCard { VStack(alignment: .leading, spacing: 10) { SDLogo(); Text("Saha Dışı; kamuya açık kaynaklardaki futbol yorumlarını, tahminleri ve maç gündemini kaynaklarıyla birlikte düzenler."); Text("Futbol sahada oynanır. Burada konuşulur.").foregroundStyle(SDTheme.muted) } }
                } else {
                    SDCard { VStack(alignment: .leading, spacing: 10) { Text("Geri bildirim").font(.headline); Text("Görüşlerini ve veri hatalarını uygulamanın yayın kanalı üzerinden bize iletebilirsin.").foregroundStyle(SDTheme.muted); Link("E-posta gönder", destination: URL(string: "mailto:feedback@sahadisi.app")!) } }
                }
            }.padding(18)
        }.background(SDTheme.background).navigationBarTitleDisplayMode(.inline)
    }
}
