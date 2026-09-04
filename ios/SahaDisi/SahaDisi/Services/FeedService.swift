import Foundation

actor FeedService {
    static let shared = FeedService()
    private let overrideKey = "sahadisi.remoteFeedURL"
    private let cacheFile = "sahadisi-feed-cache.json"

    private var productionFeedURL: String {
        (Bundle.main.object(forInfoDictionaryKey: "SahaDisiFeedURL") as? String) ?? ""
    }

    func load(forceRemote: Bool = false) async throws -> FeedPayload {
        let raw = UserDefaults.standard.string(forKey: overrideKey) ?? productionFeedURL
        if let url = URL(string: raw), !raw.isEmpty, raw.hasPrefix("https://") {
            do {
                var request = URLRequest(url: url)
                request.timeoutInterval = 12
                request.cachePolicy = forceRemote ? .reloadIgnoringLocalCacheData : .reloadRevalidatingCacheData
                request.setValue("application/json", forHTTPHeaderField: "Accept")
                let (data, response) = try await URLSession.shared.data(for: request)
                if let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) {
                    let payload = try decoder.decode(FeedPayload.self, from: data)
                    try? data.write(to: cacheURL, options: .atomic)
                    return payload
                }
            } catch { }
        }
        if let data = try? Data(contentsOf: cacheURL), let cached = try? decoder.decode(FeedPayload.self, from: data) { return cached }
        return try bundledFeed()
    }

    private var cacheURL: URL { FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appendingPathComponent(cacheFile) }
    private var decoder: JSONDecoder { JSONDecoder() }
    private func bundledFeed() throws -> FeedPayload {
        guard let url = Bundle.main.url(forResource: "seed", withExtension: "json") else { throw URLError(.fileDoesNotExist) }
        return try decoder.decode(FeedPayload.self, from: Data(contentsOf: url))
    }
}
