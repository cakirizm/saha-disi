# Saha Dışı iOS V6 — UI/UX Audit

## Tasarım hedefi
V6, onaylanan koyu spor-medya mockup'ına göre yeniden düzenlendi. Fintech/AI dashboard görünümü azaltıldı; editoryal futbol uygulaması, skor merkezi ve yorumcu veri ürünü hissi öne çıkarıldı.

## Alt navigasyon
1. Ana Sayfa
2. Maçlar
3. Keşfet
4. Yorumcular
5. Daha Fazla

## Ana Sayfa
- Saha Dışı logo kilidi ve üst kategori şeridi
- Gündem hero kartı
- Son maç skorları
- En İddialı Sözler yatay akışı
- En Çok Konuşulan Oyuncular sıralaması
- En Çok Konuşulan Takımlar sıralaması
- Öne Çıkan Yorumcular
- Pull-to-refresh

## Yorumcular
- Arama
- Tümü/Aktif/Yazar/TV/Podcast filtre görünümü
- Veri hacmine göre sıralama
- Kaynak adı + doğrulanmış yorum adedi

## Yorumcu Profili
- Büyük profil header
- Takip Et / paylaş
- Toplam yorum, doğru tahmin, yanlış tahmin, başarı oranı
- Yorumlar / İstatistikler / En Çok Konuştuğu / Hakkında tabları
- Tahmin sonucu DOĞRU/YANLIŞ rozetleri
- Oyuncu ve takım sıralamaları

## Maçlar / Maç Detayı
- Gerçek skor ve hafta
- Maça bağlı yorum adedi
- Takım odaklı maç header
- Tümü / Maç Öncesi / Maç Sonrası filtreleri
- Ölçülebilir tahminlerin sonuç rozeti

## Oyuncu Profili
- Oyuncu hero alanı
- Takip Et
- Konuşulma metrikleri
- En çok konuşan yorumcular
- Pozitif/nötr/eleştirel dağılım
- Oyuncu hakkındaki doğrulanmış kayıtlar

## Keşfet
- Global arama
- Oyuncular / Takımlar / Konular / Trendler
- Dinamik rank bar'ları
- Collector/Veri Kaynakları ekranına geçiş

## Daha Fazla
- Ayarlar
- Bildirimler
- Takip Ettiklerim
- Veri Kaynakları
- Hakkında
- Geri Bildirim

## Veri / yenileme
- 27 yorumcu
- 47 yapılandırılmış doğrulanmış kayıt
- 9 gerçek maç
- 28 farklı oyuncu
- Otomatik feed yenileme altyapısı korunuyor
- Uygulama açılışında, yeniden ön plana geldiğinde, pull-to-refresh'te ve açıkken 15 dakikada bir kontrol
- İnternet yoksa cache/fallback davranışı korunuyor

## Teknik audit
- Tüm Swift dosyaları `swiftc -parse` ile PASS
- feed.json JSON validation PASS
- seed.json JSON validation PASS
- backend/collector Python compile PASS
- Mevcut Xcode proje dosyasındaki dosyalar korunarak güncellendi; yeni Swift source eklenmediği için project.pbxproj source-list değişikliği gerekmiyor

## Not
`docs/design-reference-v6.png` onaylanan ekran referansıdır. Üretimde yorumcu/oyuncu fotoğrafları ve kulüp armaları yalnızca uygun lisans/izinle eklenmelidir; uygulama şu an güvenli placeholder/ikon sistemiyle çalışır.
