# Temuan

Catatan yang mengubah aturan skill. Yang terbaru di atas.

## 2026-11-25

- Transkrip siaran kurator untuk *Garam dan Mesiu* (3/10): yang dipuji adalah ketegangan dari detail kecil dan POV
  orang pertama yang hidup. Itu harus dipertahankan saat menulis ulang. Kurator tersandung nama tokoh saat membacakan
  sinopsis ("kenapa nama tokohnya susah banget") dan salah sebut Noémie menjadi Naomi.
- Dataset prodhokter/dataset-kbbi-indonesia (1.453 pasangan) diuji pada 100 bab: banyak salah positif (surat→surah,
  berjanji→barzanji, sup→sop) dan tidak memuat kata gaul sama sekali. Hanya subset yang diverifikasi yang dipakai
  (data/baku-terpilih.csv). Temuan nyata di bab: saklar→sakelar, piyama→piama.
- Transkrip lengkap siaran kurator (Ubin Biru, 1/10): ide, misteri, dan suasana flat dipuji. Kutipan kunci: "Bukan
  berarti seluruh narasi harus menggunakan bahasa baku, tapi sebaiknya tetap memilih kata dan ungkapan yang cukup umum
  agar cerita bisa dinikmati oleh pembaca dengan latar belakang yang beragam." Ini menegaskan register tengah, bukan baku.
  Keluhan kedua: kalimat membingungkan, narasi pendek-pendek, potongan pikiran yang belum dirangkai. Yang diperbaiki
  adalah bahasa dan sambungan kalimat; plot dan misteri dipertahankan.
- Kata kerja lisan berakhiran -in (diserahin, dilapisin, nungguin) dan "nunggu", "duluan" lolos dari daftar lama.
  Ditambahkan ke cek.py dan pemeriksa di landing page.
- Kurator menilai *Ubin Biru dari Ribeira* 1/10: bahasa percakapan Jakarta, kalimat pendek terpotong, hubungan
  antarkalimat tidak jelas. *Garam dan Mesiu* 3/10: ketegangan dan POV orang pertama berhasil, tetapi "sama", "pas",
  "terus", "nyopotnya" terlalu lisan. Dasar aturan §1 dan §2.
- Pengguna menolak dua ujung: bahasa baku kaku (tatkala, engkau, menyantap, sesungguhnya, "telah" berulang) dan
  bahasa gaul. Lahirlah register "bahasa tengah".
- Cari-ganti kata tidak cukup. Bab yang hanya diganti katanya masih terbaca potong-potong; yang naik kualitasnya adalah
  bab yang ditulis ulang utuh, dengan potongan pendek digabung memakai penghubung.
- Salah positif cek: "tanah liat" (bukan "liat" = lihat), "nyanyianku", kata pendek "-nya" yang terpisah oleh tag `<em>`.
  Sudah dikecualikan di scripts/cek.py.
- Agen latar yang menulis ulang 10 bab sekaligus berhenti di tengah karena batas pemakaian, meninggalkan draf di
  scratchpad. Cek dan salin draf (lint dulu, lalu `cmp`) sebelum menulis ulang dari nol.
- Drive tujuan bisa penuh (0 byte). Menimpa file saat disk penuh berisiko rusak; tulis di drive lain dulu.
