# Saha Dışı iOS V5 — Audit

## PASS
- 27 ana yorumcu uygulama havuzunda.
- 47 üretim kaydı; 17 yorumcuda doğrulanmış veri mevcut.
- Mustafa Çulcu'nun 9 eski benchmark kaydı üretim feed'inden çıkarıldı, `backend/calibration_statements.json` içine alındı.
- 9 gerçek benchmark maçı mevcut.
- Tüm statement -> commentator ilişkileri geçerli.
- Tüm match_id ilişkileri geçerli.
- Duplicate statement id yok.
- JSON parse: PASS.
- Python collector compile: PASS.
- Swift source syntax parse: PASS.
- iOS ekranlarında pull-to-refresh aktif.
- Uygulama foreground'a geldiğinde remote feed kontrolü aktif.
- Uygulama açıkken 15 dakikada bir feed yenileme aktif.
- Remote feed başarısızsa son cache, o da yoksa bundled seed fallback aktif.

## Yeni ekran/akışlar
1. Gündem: iddialı söz, canlı veri badge, en çok konuşulan oyuncular, öne çıkan yorumlar, takım gündemi, aktif yorumcular.
2. Keşfet: yorumcu/takım/oyuncu arama, oyuncu sıralaması, en iddialı sözler, Veri Durumu girişi.
3. Oyuncu Profili: bahis sayısı, kaç yorumcu konuştu, iddialı söz sayısı, ton dağılımı, oyuncuyu en çok konuşan yorumcular, tüm yorumlar.
4. Takım Profili: takımı en çok konuşan yorumcular + iddialı sözler.
5. Maçlar: gerçek skorlar + maç başına bağlı kayıt sayısı.
6. Maç Detayı: maç öncesi tahminler ve doğru/yanlış sonucu + maç sonrası yorumlar.
7. Yorumcular: 27 kişilik havuz, kaydı olanlar üstte, kaynak ve kayıt sayısı.
8. Yorumcu Profili: toplam yorum, iddialı söz, takım sayısı, tahmin karnesi, yorum tonu, en çok konuştuğu oyuncular/takımlar, son yorumlar.
9. Söz Detayı: özet, konu, takım, iddia gücü, güven skoru, tarih ve orijinal kaynak bağlantısı.
10. Veri Durumu: toplam kayıt/yorumcu/oyuncu, feed üretim zamanı, veri hacmi yüksek yorumcular.

## Eksik / production öncesi
- `SahaDisiFeedURL` henüz gerçek HTTPS endpoint ile doldurulmadı. Kod hazır; deploy adresi bağlanınca canlı otomatik güncelleme çalışacak.
- 10 yorumcuda henüz yayınlanmış doğrulanmış kayıt yok; 9'u için kaynak keşif eşlemesi yapıldı. Önder Özen rol değişimi nedeniyle `paused_role_change` tutuluyor.
- Gerçek yorumcu fotoğrafları ve kulüp armaları lisans/izin netleşmeden kullanılmamalı; şimdilik harf avatarları güvenli.
- Push notification yok; feed refresh var. Bildirim istenirse APNs/backend gerekir.
- Background refresh iOS tarafından garanti edilen dakikalık bir cron değildir. Veri botu server tarafında sürekli güncellenir; uygulama foreground/15 dk açık oturum/pull refresh ile yeni feed'i alır.
- Production için collector endpoint deploy, log/alert, rate limiting ve review queue admin arayüzü tamamlanmalı.
