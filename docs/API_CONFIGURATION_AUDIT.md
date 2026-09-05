# API ve yapılandırma denetimi — 5 Eylül 2026

## Sonuç ve sınırlar

Mevcut veri toplama akışı kişisel bir spor/haber/YouTube API anahtarı kullanmıyor.
Eksik bir anahtar ekleyerek açılmayı bekleyen bir API entegrasyonu bulunamadı.
Codemagic imzalama anahtarları ayrı bir gereksinimdir; spor API'leri bunların yerini tutmaz.

- Denetim başlangıcındaki 77 izlenen dosyada ve yerel Git geçmişindeki 187 commit'in diff'lerinde yaygın AWS, GitHub, Google, OpenAI anahtar kalıpları ve özel anahtar başlıkları tarandı; eşleşme bulunmadı. Bu sınırlı kalıp taraması tüm sırların yokluğunu kanıtlamaz; uzak/silinmiş Git geçmişi taranmadı.
- İzlenen `.env`, `.p8`, `.p12`, `.pem`, `.mobileprovision` dosyası bulunmadı.
- Canlı feed HTTP 200 döndü: `generated_at=2026-09-05T13:26:27.038359+00:00`, 204 yorumcu, 88 söz, 306 maç.
- TFF fikstür sayfası ve ESPN takım JSON adresi HTTP 200 döndü. Bu erişim kontrolüdür; TFF sayfasının yeniden ayrıştırılması veya bütün görsellerin kontrolü değildir.
- GitHub Actions durum API'si bu ortamda DNS hatası verdi; son iş akışlarının başarı durumu doğrulanamadı. Codemagic/App Store Connect paneli, sertifika geçerliliği ve TestFlight teslimatı doğrulanmadı.
- Dört imzalama değişkeni bu yerel süreçte yok. Bu, Codemagic'te eksik oldukları anlamına gelmez.

## Servis envanteri

| İşlev | Mevcut kaynak | Anahtar / durum |
| --- | --- | --- |
| iOS canlı feed | `Info.plist` → GitHub raw `backend/feed.json` | Anahtarsız HTTPS; erişim başarılı; önbellek/paket yedeği var |
| Fikstür/sonuç | `backend/tff_fixtures.py` → TFF | Anahtarsız HTML ayrıştırma; sezon ve takım listesi kodda sabit |
| Haber/söz | `collector_v4.py`, `collector_v3.py`, `sources.json` | Haber sayfaları ve Google News RSS; anahtarsız |
| YouTube | Kanal RSS, video sayfası, `youtube-transcript-api` | Kişisel API anahtarı tüketilmiyor; altyazı erişimi ve konuşmacı eşlemesi gerekiyor |
| Yorumcu fotoğrafı | Wikipedia, YouTube ve arama tabanlı çözümleyici | Anahtarsız; kimliği eşleşmeyen görseller atlanıyor |
| Takım arması | ESPN takım endpoint'i ve sabit görsel adresleri | Anahtarsız; belgelenmiş sağlayıcı sözleşmesi projede yok |
| Bildirim | `NotificationService.swift` / `AppStore.bootstrap` | Yeni feed yüklendiğinde yerel bildirim; APNs sunucu entegrasyonu yok |
| iOS imzalama/TestFlight | `codemagic.yaml`, `appstore` grubu | Aşağıdaki dört değişken gerekli; panel durumu bilinmiyor |
| Web prototipi | `app.js` → `data/seed.json` | Canlı iOS feed'inden ayrı, statik pilot veri |

GitHub Actions veri güncellemesi saatlik planlanıyor; bu mimari saniyelik canlı skor servisi değildir.
GitHub Actions'ın checkout/yayınlama işlemi yerleşik iş akışı token'ını kullanıyor; kodda kişisel PAT gereksinimi yok.

## Tamamlananlar

- `.gitignore`: yerel ortam dosyaları, özel anahtarlar, imzalama dosyaları ve derleme çıktıları dışlandı. Mevcut izlenen kullanıcı dosyaları silinmedi.
- `backend/server.py`: geliştirme sunucusu tüm ağ arayüzleri yerine yalnız `127.0.0.1` üzerinde dinliyor. Bu sunucu üretim servisi değildir ve backend klasörünü sunar.
- `scripts/audit_integrations.py`: sır değerlerini yazdırmadan yerel değişken varlığı, izlenen sır kalıpları, ignore kuralları, HTTPS feed ayarı ve kayıtlı veri toplama durumunu denetler.
- Codemagic'in mevcut imzalama ve TestFlight yayınlama akışı değiştirilmedi.

Denetimi depo kökünde çalıştır:

```sh
python scripts/audit_integrations.py
```

Codemagic'te `appstore` grubu yüklenmiş bir script adımında dört değişkeni zorunlu kontrol etmek için:

```sh
python3 scripts/audit_integrations.py --signing
```

Bu komut anahtarın geçerliliğini test etmez; yalnız boş olup olmadığını denetler.

## Kullanıcının kontrol etmesi gerekenler

Codemagic → uygulama/takım Environment variables → `appstore` grubunda:

| Değişken | Gerekli değer |
| --- | --- |
| `APP_STORE_CONNECT_ISSUER_ID` | App Store Connect API anahtarının issuer ID'si |
| `APP_STORE_CONNECT_KEY_IDENTIFIER` | Aynı API anahtarının key ID'si |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Aynı anahtara ait `.p8` özel anahtar içeriği |
| `CERTIFICATE_PRIVATE_KEY` | Dağıtım sertifikası için kullanılan özel anahtar; App Store Connect `.p8` anahtarından farklı |

Mevcut değerler kayıtlıysa yeniden oluşturma. Eksik olanları Codemagic'in güvenli değişken alanına ekle; sohbet veya Git deposuna yapıştırma.
Apple hesabında uygulama kimliği `com.sahadisi.app` ve projedeki takım ile uyum da gerekir.
[Codemagic resmi iOS imzalama belgesi](https://docs.codemagic.io/yaml-code-signing/signing-ios/).

Uygulama kapalıyken bildirim isteniyorsa APNs yeteneği, cihaz token kaydı, abonelikleri saklayan sunucu ve sunucuda APNs kimlik bilgileri gerekir. Sadece bir API anahtarı eklemek bu özelliği tamamlamaz. Mevcut App Store Connect anahtarı otomatik olarak APNs anahtarı değildir.

## public-apis değerlendirmesi

[public-apis](https://github.com/public-apis/public-apis) servis kataloğudur; kullanıcılara kişisel API anahtarı dağıtmaz. Listedeki servislerin kendi erişim şartları geçerlidir.

| Aday | Projedeki olası kullanım | Karar |
| --- | --- | --- |
| [API-FOOTBALL](https://www.api-football.com/pricing) | Yapılandırılmış fikstür, skor, kadro ve istatistik | Genişletme için aday. Ücretsiz planda 100 istek/gün ve sezon sınırlaması belirtiliyor. Önce hesapta Türkiye Süper Lig / 2026 sezonuna erişim doğrulanmalı. Şu an anahtar veya kod adaptörü yok; zorunlu değil. |
| [TheSportsDB](https://www.thesportsdb.com/free_sports_api) | Takım/veri/görsel yedeği | İhtiyaç halinde aday; mevcut arma kaynağı yanıt veriyor. Ayrı üretim anahtarı premium üyelikte sunuluyor. Doğrulanmış Türk yorumcu sözlerini sağlamaz. |
| [football-data.org](https://www.football-data.org/coverage) | Maç ve lig verisi | İstenen lig/sezon kapsamı doğrulanmadan alternatif olarak bağlanmamalı. |

Şu an bu servislerden birine kayıt olmak uygulamanın mevcut akışı için zorunlu değil. API-FOOTBALL denenirse ücretsiz hesap açıp sezon erişimini kontrol etmek ilk adımdır; ücretli plan satın alınmadı ve doğrulanmamış bir sağlayıcı üretime eklenmedi. Gelecekte anahtar GitHub Actions Secrets içinde tutulmalı ve yalnız backend isteğinde kullanılmalı; iOS/JavaScript içine gömülmemeli.

## Anahtar eklemenin çözmeyeceği açıklar

- Son yerel collector raporunda 79/79 kaynak başarılı görünüyor, fakat dört YouTube kaynağının her biri 0 aday üretmiş. `ok` kanal listeleme başarısını gösterebilir; altyazı üretimini garanti etmez. Altyazı hataları şu an sessizce atlanıyor, ayrıntılı ölçüm gerekli.
- Resmi YouTube altyazı indirme API'si OAuth ve videoyu düzenleme izni istiyor. Herkese açık videoların altyazılarını sıradan bir API key ile indirme çözümü değildir. [Resmi belge](https://developers.google.com/youtube/v3/docs/captions/download).
- TFF ayrıştırması sağlıksızsa önceki veri korunuyor; ayrıca manuel fikstür override'ları otomatik veriyi geçersiz kılabiliyor. Zamanla eskime ve sezon geçişi ayrıca ele alınmalı.
- iOS uzak feed hatasında önbelleğe sessizce dönebiliyor; son yenileme zamanı tek başına canlı bağlantı kanıtı değil.
- Web prototipi veri alanlarını `innerHTML` içine yerleştiriyor. Harici canlı/veri-giriş kaynağına geçirilecekse HTML kaçışlama ve URL protokol doğrulaması gerekli; bu denetimde web prototipine canlı entegrasyon eklenmedi.

Bu çalışma API/yapılandırma denetimidir; tam penetrasyon testi, bütün dış kaynakların içerik doğrulaması veya iOS cihaz testi değildir.
