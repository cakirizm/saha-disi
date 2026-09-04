import SwiftUI

struct DataStatusView: View {
    @EnvironmentObject var store: AppStore
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 16) {
                Text("Veri Kaynakları").font(.largeTitle.weight(.black))
                Text("Saha Dışı'nın canlı veri ve doğrulama durumu").foregroundStyle(SDTheme.muted)
                HStack { metric("Yorum", store.payload?.statements.count ?? 0); metric("Yorumcu", store.payload?.commentators.count ?? 0); metric("Oyuncu", store.rankedPlayers.count) }
                SDCard {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack { Circle().fill(SDTheme.green).frame(width: 8, height: 8); Text("Otomatik güncelleme aktif").font(.headline); Spacer(); if store.isRefreshing { ProgressView().tint(SDTheme.accent) } }
                        Text("Feed son üretim: \(store.payload?.generatedAt ?? "—")").font(.caption).foregroundStyle(SDTheme.muted)
                        Text("Uygulama açılışta, ön plana geldiğinde, aşağı çekildiğinde ve açıkken 15 dakikada bir yeni veri kontrol eder.").font(.caption).foregroundStyle(SDTheme.muted)
                    }
                }
                Text("Veri Hacmi Yüksek Yorumcular").font(.title3.bold())
                let rows = Array(store.rankedCommentators.prefix(12)); let maxCount = rows.first?.1 ?? 1
                SDCard {
                    VStack(spacing: 5) {
                        ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                            RankBar(rank: index + 1, name: row.0.name, count: row.1, maxCount: maxCount)
                        }
                    }
                }
            }.padding(16)
        }.background(SDTheme.background).refreshable { await store.refresh() }
    }
    private func metric(_ title: String, _ value: Int) -> some View { VStack { Text("\(value)").font(.title2.weight(.black)); Text(title).font(.caption2).foregroundStyle(SDTheme.muted) }.frame(maxWidth: .infinity).padding(10).background(SDTheme.panel).clipShape(RoundedRectangle(cornerRadius: 14)) }
}
