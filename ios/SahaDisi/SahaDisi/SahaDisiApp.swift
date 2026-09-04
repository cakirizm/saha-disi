import SwiftUI

@main
struct SahaDisiApp: App {
    @StateObject private var store = AppStore()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView().environmentObject(store).preferredColorScheme(.dark)
                .task { await store.bootstrap() }
                .task(id: scenePhase) {
                    if scenePhase == .active, store.payload != nil { await store.refresh() }
                }
        }
    }
}
