# SAHA DIŞI — iOS V6

Bu paket iOS-first Saha Dışı uygulamasının onaylanan dark sports-media tasarımına uyarlanmış sürümüdür.

Xcode projesi: `ios/SahaDisi/SahaDisi.xcodeproj`

Öncelik: iOS 17+ / SwiftUI.

Ana veri dosyaları:
- `backend/feed.json`
- `ios/SahaDisi/SahaDisi/Resources/seed.json`

Tasarım referansı:
- `docs/design-reference-v6.png`

UI audit:
- `docs/V6_UI_AUDIT.md`

Canlı production feed bağlamak için `Info.plist` içindeki `SahaDisiFeedURL` değerini sabit HTTPS feed adresine ayarla. Feed servisi remote başarısız olduğunda local/cache veriye düşer.
