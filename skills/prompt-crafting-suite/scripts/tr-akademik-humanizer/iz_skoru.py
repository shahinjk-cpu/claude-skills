"""Metindeki AI yazım izlerinin yoğunluğunu 0-100 arası kaba bir skora çevirir.

Bu bir AI dedektörü DEĞİLDİR; hiçbir dedektörün sonucunu tahmin etmez.
Yalnızca references/kaliplar.md'deki ölçülebilir izleri sayar. Eşikler kaba ayardır.

Kullanım: python -I iz_skoru.py metin.txt
"""
import re
import statistics
import sys

TR_KALIP = r"""önemli (bir )?rol|kritik|büyük önem|önem arz|hayati önem|kilit rol|dönüm noktası|çığır aç|
bu bağlamda|bu doğrultuda|bu çerçevede|söz konusu|çerçevesinde|hususunda|noktasında|
yenilikçi|kapsamlı|bütüncül|benzersiz|son teknoloji|günümüzde|son yıllarda|giderek artan|
olanak (tanı|sağla|sun)|katkı sağla|gerçekleştiril|sağlanmaktadır|niteliği taşı|hizmet etmekte|
göz önünde bulundur|mümkündür|belirtmek gerekir|dikkat çekmekte|görülmektedir|söylenebilir|
sonuç olarak|sinerji|ekosistem|katma değer|paydaş|
, (ama|ancak|fakat|oysa|lakin) |şudur:|tam da|tam anlamıyla|gerçekten de|esasen|nihayetinde|
bir bakıma|gerçek anlamda|sadece .{1,40} değil|aynı zamanda"""
EN_KALIP = r"""pivotal|crucial|vital|groundwork|complemented by|underscore|highlight|landscape|leverag|
robust|comprehensive|novel|seamless|testament|delve|foster|showcas|in order to|serves as"""
SIRA = r"\b(Birincisi|İkincisi|Üçüncüsü|Dördüncüsü|Firstly|Secondly|Thirdly)\b"

# (ad, ağırlık, açıklama)
OLCUTLER = [
    ("noktali_virgul", 25, "cümle başına noktalı virgül (0,6 ve üstü = tam puan)"),
    ("uzun_cumle", 20, "40+ kelimelik cümle oranı (%25 ve üstü = tam puan)"),
    ("tekduzelik", 20, "cümle uzunluklarının birbirine benzerliği (değişim katsayısı 0,6 ve üstü = sıfır)"),
    ("kalip", 25, "100 kelimede katalog ifadesi (2 ve üstü = tam puan)"),
    ("sira_sozcugu", 10, "1000 kelimede Birincisi/İkincisi… (1,5 ve üstü = tam puan)"),
]


def cumleler(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ(\"])", text.strip())
    return [s for s in parts if len(s.split()) >= 3]


def skor(text):
    sents = cumleler(text)
    if not sents:
        return {"skor": 0, "parcalar": {}}
    words = len(text.split())
    lens = [len(s.split()) for s in sents]
    turkce = len(re.findall(r"[çğışöüÇĞİŞÖÜ]", text)) > len(text) * 0.005
    kalip = re.compile((TR_KALIP if turkce else EN_KALIP).replace("\n", ""), re.I)
    cv = statistics.pstdev(lens) / statistics.mean(lens) if len(lens) > 1 else 0
    oran = {
        "noktali_virgul": min(text.count(";") / len(sents) / 0.6, 1),
        "uzun_cumle": min(sum(l >= 40 for l in lens) / len(sents) / 0.25, 1),
        "tekduzelik": 1 - min(cv / 0.6, 1) if len(lens) > 2 else 0,
        "kalip": min(len(kalip.findall(text)) / words * 100 / 2, 1),
        "sira_sozcugu": min(len(re.findall(SIRA, text)) / words * 1000 / 1.5, 1),
    }
    parcalar = {ad: round(oran[ad] * w, 1) for ad, w, _ in OLCUTLER}
    return {"skor": round(sum(parcalar.values())), "parcalar": parcalar}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    r = skor(open(sys.argv[1], encoding="utf-8").read())
    print(f"AI iz skoru: {r['skor']}/100  (dedektör sonucu değildir)")
    for ad, w, aciklama in OLCUTLER:
        print(f"  {ad:15} {r['parcalar'].get(ad, 0):5}/{w}  {aciklama}")
