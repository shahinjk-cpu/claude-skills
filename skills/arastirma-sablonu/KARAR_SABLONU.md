# KARAR: [proje adı]

Bu dosya araştırma kapısının kayıt defteridir. Kurallar sonuçlardan önce yazılır. Sonradan yapılan her değişiklik
"Sapmalar" bölümüne tarih ve gerekçeyle eklenir; eski satırlar silinmez.

## Soru

- **Temel yöntem:** [makale, kod, sürüm]
- **Ölçülmüş bozulma:** "[yöntem], [koşul] altında [ölçüt]'te [A]'dan [B]'ye düşüyor." (tarih, kaç tohum)
- **Kapı 1 sorusu (bozulmadan önce yazılır, dondurulmuş):** [soru] · koşul düzeyleri: [stressiz düzey dahil] · eşik:
  [sayılan düşüş, ölçüt biriminde] · ölçüt: [tek ölçüt] (tarih, commit)
- **Tez cümlesi (dondurulmuş):** [tek cümle] (tarih)
- **Bozulma nasıl ölçüldü:** [kendi koşumuz mu; resmî/yeniden üretilmiş kod mu; stres yokken sayı makaledekiyle aynı
  ortamda karşılaştırıldı mı; deneme ve tohum sayısı; düşüş tohum dağılımından büyük mü]. Literatürden, oyuncaktan ya da
  ajanın çıkarımından gelen düşüş yalnız hipotezdir.

## Aile kontrolü

- **Koşul / görev:** [değiştirdiği fiziksel büyüklük ya da iş; anahtar kelime değil]
- **Taranan kaynaklar:** [kişisel klasördeki kapali_kapilar.json, hafıza, kayıt, önceki projelerin karar ve sonuç dosyaları]
- **Daha önce aynı koşulda çalıştık mı:** [proje, tarih ya da "yok"; orada basit bir kural ya da rakip kazandı mı, düşüş
  eşiğin altında mı kaldı]
- **Kazanan basit kuralın buradaki karşılığı:** [ilk ölçüme girer]
- **Bu kez neden farklı (ölçülebilir öngörü):** ["önceki X, eşik Z; bu kez en az Z bekliyorum, çünkü ...; ilk ölçüm sınar";
  yoksa çalışma başlamaz]

## Üç sayı

| Koşul | Taban | En güçlü basit çare | Adil kâhin | Kâhin − çare | Tohum |
|---|---|---|---|---|---|
| | | | | | |

- **Basit çare adayları:** [o alanın uygulayıcısının ilk deneyeceği en ucuz 3+ çare; yöntemi bilmeyen bir ajandan;
  her biri ölçüldü ya da gerekçeyle elendi]
- **En güçlü basit çare nedir, ne zaman kuruldu:** [yöntemden önce mi? yönteme verilecek ayar taraması ona da verildi mi?]
- **Adil kâhin nasıl tanımlandı:** [neyi, ne zamandan itibaren biliyor; kim/nasıl belirledi; tanımlanamıyorsa neden]

**Boşluk cümlesi:** "[Yöntem], [koşul] altında [ölçüt]'te [X] kadar düşüyor. Kâhin [Y] kazandırıyor. En iyi basit
çare [Z] kadarını kapatıyor. Geriye kalan [Y − Z] hedefimiz."

## Protokol (ana koşudan önce)

- **Karar kuralı:** [örn. yöntem − en güçlü rakip ≥ δ ve aralığın alt ucu > 0]
- **Eşik δ:** [değer ve gerekçe]
- **Tohum:** [≥ 3; daha azı pilottur: kapı geçirmez, sınırlılık olarak yazılır. Eğitim mi, değerlendirme tohumu mu
  (hazır checkpoint: farklı başlangıç kümeleri, eşli test); tek eğitim koşusu sınırlılıktır]
- **Pilot bütçesi:** [en fazla kaç koşu / saat; pilot sayıları üç sayı tablosuna ve tez cümlesine girmez]
- **Varsayımlar ve bozulursa ne olur:** [her varsayım için: bozulursa sonuç nasıl değişir, nasıl anlaşılır]
- **Koşullar ve ölçüt:** [başarısız koşu nasıl sayılır]
- **Kilitli test kümesi / ayrılmış koşullar:** [ayar için hiç kullanılmayan]
- **Rakip adaleti:** [aynı bütçe, aynı tarama, aynı ayrıcalıklı bilgi]
- **Benzetimin kusursuzlukları:** [liste; sonuç hangisine dayanıyor]
- **Gerçek dünya testi:** [platform, erişim, benzetimle eşleşme (Kapı 2'de sorulur); koşul × deneme × tohum, tarih.
  Eşleşen platform yoksa sonuçtan önce sınırlılık; sonuçtan sonra vazgeçilirse Sapma]
- **Durma kuralı:** "3 kapı kapanırsa / 2 tasarım denemesi tutmazsa olumsuz sonucu yazar, dururum." (Kapalı kapı:
  ölçülmüş boşluğun eşiğin altında kaldığı ya da basit çarenin yettiği bir koşul. Dönüş: yeni bir koşula, soruya ya da
  yönteme geçiş; sonuç olumlu ya da olumsuz olsun, sayılır.)

## Kapı kayıtları

| Tarih | Kapı | Karar | Not |
|---|---|---|---|
| | | | |

## Yöntem arama (Kapı 3'ten sonra)

| Tarih | Kâhin ne biliyor | Basit çareler (ölçüldü mü) | Boşluğun nedeni (kanıt) | Gereken özellik | Literatür (yayımlanmış mı) | Şeytanın avukatı: 3 neden | En küçük test |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Aktarım (başka alandan yöntem)

| Tarih | Bozulan parça (ölçüm) | Gereken özellik (alandan bağımsız) | Kaynak alan | O alanın basit aracı (sonuç) | Kaynak varsayımı burada geçerli mi | Parçanın kâhin tavanı |
|---|---|---|---|---|---|---|
| | | | | | | |

## Aktarım çalışması (calisma_turu: aktarim)

- **M ve neden o:** [alanın güncel güçlü ya da standart yöntemi; daha güçlüsü varsa neden seçilmedi]
- **Darboğaz (kendi koşumuzda):** "M, [koşul] altında [eksen ölçütü]'nde [değer]; [kullanım] için [hedef] gerekir." (tarih, tohum)
- **Avantaj ekseni (aday adından önce, dondurulmuş):** [eksen] · ölçüt: [ölçülen davranış] · yön: [büyük/küçük iyi]
- **δ (ana ölçütte eşdeğerlik payı) ve ε (eksende sayılan üstünlük):** [değerler; δ ≤ ½·(M − taban); ε'un kullanımdan gerekçesi]
- **Sonuç A cümlesi:** [...] · **Sonuç B cümlesi:** [...]
- **Gereken tohum:** [n; `tools/aralik.py tohum` ile, sd kaynağı]
- **Akıldaki yöntem fikirleri (aday değil, Kapı A3'ten önce):** [...]

| Tarih | Basit alternatif | Tür (ucuz_ek / klasik / küçük M …) | Ölçüldü mü, sonuç |
|---|---|---|---|
| | | | |

| Tarih | Aday (en çok 2) | Kaynak makale | Alan | Neden ekseni oynatmalı | Nerede kötü olmalı | Şeytanın avukatı | Oyuncak test |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

| Tarih | Aday ↔ basit | Tohum | Perf. aday − M (%90) | Perf. basit − aday (%90) | Eksen aday − basit (%90) | Sonuç (A / B / belirsiz / pilot) |
|---|---|---|---|---|---|---|
| | | | | | | |

## Dönüş sayacı

| # | Tarih | Neden | Kim onayladı |
|---|---|---|---|
| | | | |

## Aşılan kapı kararları

| Tarih | Kapı | Ajanın kararı | Kullanıcının gerekçesi |
|---|---|---|---|
| | | | |

## Sapmalar

1. (henüz yok)
