# Saha Dışı kaynak erişimi — 5 Eylül 2026

## Şu anda uygulananlar

- TFF fikstürü okunuyor. Boş/eski elle girilmiş skorlar güncel sonucu silemiyor. 4 Eylül Başakşehir–Galatasaray sonucu **2–3**; [Galatasaray maç raporu](https://www.galatasaray.org/haber/futbol/basaksehir-2-3-galatasaray/60892) ve [Başakşehir raporu](https://ibfk.com.tr/haberler/istanbul-basaksehir-2-3-galatasaray) kayıtla birlikte saklanıyor.
- Tarihi geçmiş ama skoru olmayan maç “Sonuç bekleniyor” gösteriliyor. Saatler İstanbul saatine göre yorumlanıyor. Erteleme/iptal/bitiş ayrı durumlar.
- Haber sitelerinin OG görselleri/logo dosyaları yorum görseli olarak kullanılmıyor. Kimliği doğrulanmış yorumcu fotoğrafı; bulunamazsa baş harfleri kullanılıyor. Takım görseli yalnızca takım arması kaydından geliyor.
- 207 kişilik liste, her çalışmada 30 kişi döndürülerek taranıyor. Yağız Sabuncuoğlu, Ertan Süzgün, Fabrizio Romano, David Ornstein ve Gianluca Di Marzio ayrıca her turda aranıyor.
- Haber, sosyal platform ve ajans alan adları için arama indeksi üzerinden keşif var. Bu yöntem tüm X/Instagram paylaşımlarına erişim sağlamaz; sonuç bulunamaması paylaşım yapılmadığı anlamına gelmez.
- X recent search ve Instagram Business Discovery için sunucu okuyucuları var. Anahtar yoksa sağlık kaydında `missing_credentials` görünür. Başlangıç hesap eşleştirmesi Romano içindir; diğer yorumcuların gerçek hesapları kanıt bağlantısıyla `backend/social_accounts.json` dosyasına eklenmelidir.
- YouTube kanal/video taraması mevcut. Başlıkta tek isim bulunması konuşmacıyı kanıtlamaz; yeni altyazı adayları inceleme kuyruğuna gider. Video sesi için otomatik konuşmacı doğrulaması yapılmıyor.
- Bir transfer sözünün kaynağına doğrulanmış biçimde bağlanması, transferin gerçekleştiğini kanıtlamaz. Muhabir aktarımları “Transfer iddiası” olarak gösterilir. Otomatik resmî transfer onayı sistemi henüz yok.

## Başvurular

| Kaynak | Başvuru ve istenecek erişim | Projedeki durum |
|---|---|---|
| X | [Developer Console](https://console.x.com/) üzerinden geliştirici uygulaması oluştur; salt okunur post arama kullanımını açıkla; faturalama/kredileri ve harcama sınırını belirle; Bearer Token oluştur. [Arama API](https://docs.x.com/x-api/posts/search-recent-posts), [kullanım ve ücretlendirme](https://docs.x.com/x-api/fundamentals/post-cap). | `X_BEARER_TOKEN` ile devreye girer. Hesap başına turda en fazla 20 son gönderi; daha fazlası varsa `partial=true`. Tam arşiv taraması yok. |
| YouTube | [Google Cloud Console](https://console.cloud.google.com/) içinde proje aç, YouTube Data API v3 etkinleştir. Kanal/video keşfi için API key; kullanıcı yetkisi gerektiren işlemler için OAuth istemcisi oluştur. [Başlangıç](https://developers.google.com/youtube/v3/getting-started), [altyazı indirme](https://developers.google.com/youtube/v3/docs/captions/download). | Şu an kanal RSS/erişilebilir altyazı okuyucusu var; Data API anahtarı bağlantısı eklenmedi. API key başkalarının bütün videolarının altyazı indirme iznini sağlamaz. Yayıncıdan transkript/kullanım izni iste. |
| Instagram | [Meta for Developers](https://developers.facebook.com/) üzerinden uygulama ve uygun Instagram API ürününü oluştur. Profesyonel hesap bağlantısı, ilgili izinler ve gerektiğinde App Review sürecini tamamla. [Business Discovery](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery/). | Facebook Login tabanlı Business Discovery okuyucusu hazır; tüm bireysel hesapları veya tüm Instagram'ı arayan API değildir. Meta dokümanına bu araştırmada erişim hatası alındı; uygulama panelindeki güncel ürün/izin koşullarını başvuru sırasında doğrula. |
| Anadolu Ajansı | [AA abonelik sayfası](https://www.aa.com.tr/tr/p/abonelik-talepleri): `abone@aa.com.tr`; kurum adı, iletişim ve yayın mecrasıyla başvur. Spor, transfer, alıntı, fotoğraf ve mobil yeniden yayın kapsamını belirt. | Açık kaynak keşfi var; lisanslı ajans API/akış bağlantısı için abonelik sözleşmesi ve teknik doküman gerekir. |
| DHA | [Abonelik başvurusu](https://dhaabone.dha.com.tr/sign-in) içindeki formu doldur. Mobil uygulama ve spor servisini belirt. | Lisanslı servis henüz bağlı değil. |
| İHA | [Başvuru formu](https://abone.iha.com.tr/Abonelik/Basvurusu) veya `abone@iha.com.tr`. [İletişim](https://www.iha.com.tr/iletisim). | Lisanslı servis henüz bağlı değil. |
| Reuters | [Medya içerik çözümleri](https://reutersagency.com/who-we-serve/media/) üzerinden satış ekibine spor metni, kısa alıntı, görsel ve mobil dağıtım talebi ilet. | Lisanslı servis henüz bağlı değil. |
| Maç verisi | [API-Football başlangıç rehberi](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide) üzerinden hesap aç; Süper Lig güncel sezon, skor, kadro, olaylar ve istatistik kapsamını dene. Ticari kullanım ve arma haklarını sor. | Şu an TFF ve saatlik GitHub Actions kullanılıyor. Saniyelik canlı skor hizmeti değil. API-Football entegrasyonu henüz yok; servis seçilip erişim alınınca ayrı bağlanmalı. |

Fiyatlar ve izin kapsamı sağlayıcının paneli/sözleşmesi üzerinden kesinleşir. Başvuru veya abonelik satın alma işlemi bu çalışma sırasında yapılmadı.

## Anahtarları ekleme

GitHub deposu → **Settings → Secrets and variables → Actions**:

- Secrets: `X_BEARER_TOKEN`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`.
- Variables: `META_GRAPH_VERSION` — Meta uygulamasında kullanılan desteklenen sürüm, örneğin `vNN.0` biçiminde gerçek sürüm numarası.
- Anahtarları iOS uygulamasına, kaynak koda veya sohbete yazma.
- `backend/social_accounts.json`: yorumcu ID, platform (`x`/`instagram`), gerçek kullanıcı adı, kimliği kanıtlayan URL ve `verified_identity` alanları. Görünen hesap adı veya mavi tik tek başına yeterli değildir.
- Actions → **Saha Disi Live Feed → Run workflow**. `backend/collector_health.json` kaynak bazında bağlantı sonuçlarını, `backend/fixture_health.json` TFF güncelliğini gösterir. `ok=true` bütün platformun tarandığı anlamına gelmez.

## Transfer muhabiri araştırma listesi

| İsim | Doğrulama/araştırma kaynağı | İzleme biçimi |
|---|---|---|
| Yağız Sabuncuoğlu | [Sports Digitale bağlantısını paylaştığı profil](https://tr.linkedin.com/posts/yagizsabuncuoglu_sports-digitaledeki-3-videomuz-24-saatte-activity-7037704194409017344-ccIq) | Mevcut kadroda; haber/sosyal/ajans keşfi. X/Instagram hesap kimliği ayrıca eşleştirilmeli. |
| Ertan Süzgün | Mevcut proje kadrosu; hesap kimlik kontrolü bekliyor. | Her tur arama; doğrulanmadan sosyal API hesabı eklenmez. |
| Fabrizio Romano | [Kendi platform bağlantıları](https://linktr.ee/fabrizioromano) | X/Instagram başlangıç eşleştirmesi ve her tur arama. |
| David Ornstein | [The Athletic yazar sayfası](https://www.nytimes.com/athletic/author/david-ornstein/) | Kadroya eklendi; her tur arama. Ücretli yazılar için abonelik/izin gereksinimi ayrıca ele alınmalı. |
| Gianluca Di Marzio | [Kendi haber sitesi](https://www.gianlucadimarzio.com/) | Kadroya eklendi; her tur arama. Sitedeki başka yazarların sözleri Di Marzio'ya atfedilmez. |

Hiçbir muhabire koşulsuz “doğru bilgi” etiketi verilmiyor. Aynı haberin farklı sitelerde kopyalanması bağımsız doğrulama sayılmaz. Kulüp/KAP duyurusu, oyuncu, kulüp kimlikleri ve asıl kaynak birlikte doğrulanmadan kesinleşmiş transfer ve yeni kulüp arması üretilmemeli. Mevcut İngilizce içerikler özgün dilinde tutulur; otomatik çeviri alıntı yerine geçirilmez.

## Ajans/yayıncıya gönderilecek taslak

> Merhaba, Saha Dışı adlı iOS futbol uygulaması için spor ve transfer içerik servislerinize başvurmak istiyoruz. Yorumcu ve muhabirlerin kısa, birebir alıntılarını isim, tarih ve asıl kaynak bağlantısıyla göstereceğiz. Mobil uygulamada ticari yayın, kısa alıntı, bildirim, arşivleme ve uygun fotoğraf/arma kullanım haklarını kapsayan teklifinizi rica ederiz. API/RSS/JSON/XML teslim seçenekleri, güncelleme sıklığı, düzeltme/silme bildirimleri, kota ve ücret bilgilerini paylaşabilir misiniz? Kurum/yetkili: […], uygulama/site: […], beklenen aylık kullanıcı: […], iletişim: […].

Bu bir taslaktır; kimseye gönderilmedi.
