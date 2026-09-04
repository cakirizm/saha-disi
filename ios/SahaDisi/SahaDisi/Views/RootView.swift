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
                NavigationLink { NotificationSettingsView() } label: { menu("Bildirimler", "bell") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Takip Ettiklerim", icon: "heart") } label: { menu("Takip Ettiklerim", "heart") }.buttonStyle(.plain)
                NavigationLink { DataStatusView() } label: { menu("Veri Kaynakları", "shippingbox") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Hakkında", icon: "info.circle") } label: { menu("Hakkında", "info.circle") }.buttonStyle(.plain)
                NavigationLink { MoreDetailView(title: "Geri Bildirim", icon: "rectangle.and.pencil.and.ellipsis") } label: { menu("Geri Bildirim", "rectangle.and.pencil.and.ellipsis") }.buttonStyle(.plain)
                VStack(spacing: 10) {
                    SDLogo(); Text("v1.0.0").font(.caption2).foregroundStyle(SDTheme.muted2)
                    Text("Futbol sahada oynanır. Burada konuşulur.").font(.caption).foregroundStyle(SDTheme.muted)
                    if let last = store.lastRefreshAt { Text("Son uygulama yenilemesi: \(last.formatted(date: .omitted, time: .shortened))").font(.caption2).foregroundStyle(SDTheme.muted2) }
                }.frame(maxWidth: .infinity).padding(.top, 60)
            }.padding(18)
        }.background(SDTheme.background)
    }
    private func menu(_ title: String, _ icon: String) -> some View {
        HStack(spacing: 14) { Image(systemName: icon).frame(width: 24); Text(title).font(.body.weight(.medium)); Spacer(); Image(systemName: "chevron.right").font(.caption).foregroundStyle(SDTheme.muted2) }
            .padding(.vertical, 17).overlay(alignment: .bottom) { Rectangle().fill(SDTheme.line).frame(height: 1) }
    }
}

struct NotificationSettingsView: View {
    @StateObject private var notifications = NotificationService.shared
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 12) {
                    Image(systemName: "bell.badge").font(.title2).frame(width: 46, height: 46).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 13))
                    VStack(alignment: .leading, spacing: 2) { Text("Bildirimler").font(.largeTitle.black()); Text("Ne için bildirim istediğini sen seç.").font(.caption).foregroundStyle(SDTheme.muted) }
                }
                SDCard {
                    VStack(alignment: .leading, spacing: 12) {
                        Toggle(isOn: Binding(get: { notifications.allEnabled }, set: { value in Task { await notifications.setAll(value) } })) {
                            VStack(alignment: .leading, spacing: 3) { Text("Tüm Bildirimler").font(.headline); Text("Yeni doğrulanmış her yorum geldiğinde bildirim al.").font(.caption).foregroundStyle(SDTheme.muted) }
                        }
                        Text("Takım bildirimi için takım sayfasındaki zil simgesini; yorumcu bildirimi için yorumcu profilindeki Bildirimler menüsünü kullanabilirsin.")
                            .font(.caption).foregroundStyle(SDTheme.muted)
                        Text("Takım + yorumcu filtresi: Bir takım sayfasından yorumcu profiline girdiğinde yalnız o yorumcunun o takımla ilgili yeni yorumlarını açabilirsin.")
                            .font(.caption).foregroundStyle(SDTheme.muted)
                    }
                }
                if !notifications.teamNames.isEmpty { preferenceCard("Takım Bildirimleri", values: notifications.teamNames.sorted()) }
                if !notifications.commentatorIDs.isEmpty { preferenceCard("Yorumcu Bildirimleri", values: notifications.commentatorIDs.sorted()) }
                if !notifications.commentatorTeamKeys.isEmpty { preferenceCard("Takım + Yorumcu", values: notifications.commentatorTeamKeys.sorted()) }
            }.padding(18)
        }.background(SDTheme.background).navigationBarTitleDisplayMode(.inline)
    }
    private func preferenceCard(_ title: String, values: [String]) -> some View {
        SDCard { VStack(alignment: .leading, spacing: 8) { Text(title).font(.headline); ForEach(values, id: \.self) { Text("• \($0.replacingOccurrences(of: "|", with: " · "))").font(.caption).foregroundStyle(SDTheme.muted) } } }
    }
}

struct MoreDetailView: View {
    @EnvironmentObject var store: AppStore
    @StateObject private var notifications = NotificationService.shared
    let title: String
    let icon: String
    @State private var liveDataEnabled = true
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                HStack(spacing: 12) { Image(systemName: icon).font(.title2).frame(width: 46, height: 46).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 13)); Text(title).font(.largeTitle.black()) }
                if title == "Ayarlar" {
                    SDCard { Toggle("Canlı veri yenileme", isOn: $liveDataEnabled) }
                } else if title == "Bildirimler" {
                    SDCard {
                        Toggle(isOn: Binding(get: { notifications.allEnabled }, set: { value in Task { await notifications.setAll(value) } })) {
                            VStack(alignment: .leading, spacing: 3) { Text("Tüm Bildirimler").font(.headline); Text("Yeni doğrulanmış her yorum için bildirim al.").font(.caption).foregroundStyle(SDTheme.muted) }
                        }
                    }
                    NavigationLink { NotificationSettingsView() } label: { Label("Tüm bildirim tercihlerini yönet", systemImage: "slider.horizontal.3").font(.headline).foregroundStyle(SDTheme.accent) }
                } else if title == "Takip Ettiklerim" {
                    SDCard { Text("Takım ve yorumcu bildirim tercihlerini ilgili profil sayfalarındaki zil düğmelerinden yönetebilirsin.").foregroundStyle(SDTheme.muted) }
                } else if title == "Hakkında" {
                    SDCard { VStack(alignment: .leading, spacing: 10) { SDLogo(); Text("Saha Dışı; doğrulanmış futbol yorumlarını, tahminleri ve maç gündemini kaynaklarıyla birlikte düzenler."); Text("Futbol sahada oynanır. Burada konuşulur.").foregroundStyle(SDTheme.muted) } }
                } else {
                    SDCard { VStack(alignment: .leading, spacing: 10) { Text("Geri bildirim").font(.headline); Text("Görüşlerini ve veri hatalarını bize iletebilirsin.").foregroundStyle(SDTheme.muted); Link("E-posta gönder", destination: URL(string: "mailto:feedback@sahadisi.app")!) } }
                }
            }.padding(18)
        }.background(SDTheme.background).navigationBarTitleDisplayMode(.inline)
    }
}
