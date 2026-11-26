# novel-bahasa-tengah

Skill Claude Code untuk menulis dan menulis ulang novel berbahasa Indonesia dalam **bahasa tengah**: tidak baku kaku,
tidak gaul. Bahasanya seperti novel populer yang rapi, mudah dipahami pembaca dari daerah mana pun.

Dibuat dari dua penilaian kurator atas novel penulis sendiri (1/10 dan 3/10) dan dari skill
[lugas](https://github.com/bryankwandou/lugas). Isinya:

- `SKILL.md`: register, daftar kata yang dihindari dan penggantinya, aturan kalimat, alur kerja per bab.
- `scripts/cek.py`: pemeriksa bab. Menandai kata lisan, kata kaku, "telah" berulang, penghubung lisan yang menumpuk,
  tanda pisah panjang, frasa khas tulisan mesin, dan bab di bawah batas kata.
- `references/`: daftar pilihan kata literer dan checklist narasi (dari skill auditor-bahasa-novel-indonesia).
- `data/baku-terpilih.csv`: ejaan baku yang sudah diverifikasi.
- `TEMUAN.md`: catatan temuan yang mengubah aturan. Diperbarui setiap ada temuan baru.

## Pasang

```bash
git clone https://github.com/bryankwandou/novel-bahasa-tengah ~/.claude/skills/novel-bahasa-tengah
```

## Cek bab

```bash
python ~/.claude/skills/novel-bahasa-tengah/scripts/cek.py path/ke/bab 1 50 --min 1500
```

File bab bernama `001.txt`, `002.txt`, dan seterusnya. Baris pertama adalah judul.

## Contoh

Sebelum: *"Kancingnya kutuang ke baskom. Pelan, segenggam-segenggam, biar nggak ada yang loncat ke lantai."*

Sesudah: *"Kancing itu kutuang ke baskom plastik, pelan dan segenggam demi segenggam supaya tidak ada yang meloncat ke lantai."*

Lisensi MIT.
