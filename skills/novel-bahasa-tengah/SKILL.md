---
name: novel-bahasa-tengah
description: Menulis dan menulis ulang bab novel berbahasa Indonesia untuk Wattpad/KaryaKarsa dalam "bahasa tengah" (tidak baku kaku, tidak gaul), lalu lint dan terbitkan ulang. Gabungan skill lugas (pola tulisan AI, struktur), auditor-bahasa-novel-indonesia (PUEBI, pilihan kata, ketegangan, POV), pedoman novel Bryan Kwandou, dan alur terbit KaryaKarsa. Pakai saat diminta menulis bab baru, memperbaiki bahasa bab, menaikkan nilai kurator, atau mengaudit novel Indonesia.
---

# Novel bahasa tengah

Dibuat 2026-11-25 dari: `lugas` (C:\Users\arche\.claude\skills\lugas), `auditor-bahasa-novel-indonesia`,
E:\Download\bryan-kwandou\novels\PEDOMAN-BAHASA-BAKU.md, dan alur ~/.higgsfield/kk. Kalau berbeda, urutan menang:
keputusan pengguna terbaru > pedoman novel > skill ini > lugas/auditor.

## 1. Register: bahasa tengah

Seperti novel populer yang rapi: kosakata sehari-hari yang dipahami pembaca dari daerah mana pun, kalimat lancar.

| Hindari (kaku/arkais) | Pakai |
|---|---|
| tatkala, kala itu | saat, ketika |
| engkau, dikau | kamu |
| nan, adapun, hendak | yang, (buang), mau/ingin |
| menyantap, bersantap | makan |
| sesungguhnya | sebenarnya |
| telah (berulang) | sudah |
| ia (di semua tempat) | dia dan ia bergantian |

| Hindari (gaul/Jakarta) | Pakai |
|---|---|
| nggak/enggak/gak | tidak, tak |
| udah, banget, kayak, aja, doang | sudah, sekali/sangat, seperti, saja, hanya |
| gitu/gini/gimana, emang | begitu/begini/bagaimana, memang |
| bikin, kelar, ngapain, bilang, ngomong | membuat, selesai, untuk apa, berkata/bilang (dialog boleh), bicara |
| ngerti, mikir, inget, seneng, capek | mengerti, berpikir, ingat, senang, lelah |
| kasih, abis, dateng, liat, ketemu, nemu, nyari | memberi, habis/setelah, datang, lihat, bertemu, menemukan, mencari |
| cuma, bareng, gede, bener/beneran, barusan, bego | hanya, bersama, besar, benar/sungguh, baru saja, bodoh |
| sama (dan), pas (saat), terus (lalu) | dan/dengan, saat, lalu |
| ng-/ny-/-in lisan (ngitung, nyopot, bersihin) | menghitung, melepas, membersihkan |
| sih, dong, deh, kok, nih, tuh | buang; "kan", "ya", "tak" boleh di dialog |

Dialog: santai tetapi bersih. "Kamu sudah makan?" "Jangan begitu." "Aku tidak tahu."

Daftar padanan lengkap dan checklist narasi: references/pilihan-kata-literer.md dan references/checklist-narasi.md (tanda (K) = terlalu kaku untuk register ini).

## 2. Kalimat (masalah kurator: potongan pendek, hubungan tidak jelas)

- Gabungkan potongan berurutan dengan penghubung: karena, sehingga, sementara, ketika, lalu, tetapi, padahal.
- Setiap kalimat jelas siapa melakukan apa. Paragraf narasi 3 sampai 6 kalimat yang terhubung.
- Kalimat pendek hanya di puncak ketegangan, beberapa per adegan.
- Tidak berbunga-bunga, tanpa kiasan klise, detail konkret tetap (bunyi, bau, tangan, benda).
- Pola AI dari lugas tetap dibuang: penjelasan ulang yang baru dibaca, daftar tiga simetris, akhir yang merangkum,
  frasa "menggantung di udara", "waktu seakan berhenti", "tanpa sadar menahan napas".

## 3. Isi dan larangan tetap

1. Plot, urutan adegan, nama, angka, tanggal, dialog, akhir bab tidak berubah. Tidak ada fakta atau tokoh baru.
2. Tanpa tanda pisah panjang (— – --). Tanpa unsur Indonesia (tempat, makanan, sapaan pak/bu/mas/kak/om/tante, ktp).
3. Minimal 1.500 kata per bab di luar judul. Baris pertama file = judul. Tag `<em>` dipertahankan.
4. Adegan ranjang kiasan. Kekerasan boleh di halaman, tanpa detail cara membunuh atau dosis obat.

## 4. Alur kerja per bab

1. Baca bab utuh. Catat fakta: nama, angka, urutan adegan, kalimat akhir.
2. Tulis ulang seluruh bab sekaligus (bukan cari-ganti kata), mengikuti §1 dan §2.
3. Simpan, jalankan `python scripts/cek.py FOLDER_BAB NNN NNN` (skrip skill ini) dan `python lint.py NNN NNN` di folder
   novel kalau ada (lint novel juga memeriksa unsur Indonesia). Target: tanpa KATA/DASH/AI/KAKU, LISAN 0, PENGHUBUNG
   wajar (sisa sah: "sama" = serupa, "terus" = terus-menerus, "pas" = cocok, "bilang" di dialog). "tanah liat" bukan lisan.
   Temuan baru (kata lolos, salah positif, keluhan kurator) dicatat di TEMUAN.md dan daftar di §1 serta cek.py diperbarui.
4. Kalau drive E penuh (cek `(Get-PSDrive E).Free`), tulis dulu ke scratchpad di C:, lint di sana, lalu salin dan `cmp`.
5. Jangan menyerahkan ke agen latar kalau pengguna minta kerja di agen utama.

## 5. Terbit ulang ke KaryaKarsa

Browser Antigravity CDP 9223 (lihat memori). Dari C:\Users\arche\.higgsfield:
`bash kk/g/rungantiisi.sh garam|ubin DARI SAMPAI` (peta post di kk/g/peta.txt, log kk/g/gantiisi.log).
Gambar lama dipertahankan. Harga: bab 1 sampai 15 Gratis, 16+ Rp 3.000.

## 6. Audit dan nilai (bila diminta)

Format auditor: Kekuatan (2 sampai 4) → Saran (sebelum → sesudah + alasan) → Nilai 1 sampai 10 + alasan.
9-10 rapi dan siap terbit; 7-8 sisa sedikit kata lisan; 5-6 masih lisan; 3-4 banyak salah; 1-2 sulit dibaca.
Checklist A sampai F dan contoh audit sinopsis Garam dan Mesiu: references/checklist-narasi.md. Komentar selalu dalam
bahasa Indonesia.

## 7. Kurasi naskah utuh (bila diminta)

Diadaptasi dari ns-manuscript-evaluator (leemain88/novel-skills, MIT). Beri nilai 1 sampai 10 untuk enam pilar, masing-masing
dengan bukti dari bab dan adegan nyata: struktur cerita, kedalaman tokoh, tempo, dampak emosi, kekhasan suara, orisinalitas.
Tambahkan pilar ketujuh yang dinilai kurator Indonesia: bahasa (register, kelancaran kalimat, PUEBI). Tutup dengan tiga
kekuatan untuk sinopsis dan tiga bagian yang perlu dipoles. Nilai jujur; jangan menaikkan angka karena diminta.

Kurator membaca sinopsis dengan suara keras. Sinopsis harus enak diucapkan: nama tokoh yang sulit dilafalkan
(kurator tersandung "Noémie Castel", "Julien") cukup ditulis sekali dengan ejaan asli, lalu dipakai konsisten.

## 8. Sumber

lugas (bryankwandou/lugas), auditor-bahasa-novel-indonesia (dari pengguna), leemain88/novel-skills (MIT, pilar kurasi),
prodhokter/dataset-kbbi-indonesia (MIT, dipakai sebagian setelah diverifikasi: data/baku-terpilih.csv). Pembanding yang
dibaca: alvinindra/bahasa-skills, fathurwithyou/indonesia-eyd-writing-skill, barkahss/simple-indonesia,
nozomicreative/lancar-indonesia. Tidak satu pun menangani ragam cakapan fiksi (sama, pas, terus, nyopotnya); aturan itu
ditulis sendiri di §1.
