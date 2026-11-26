"""cek.py FOLDER_BAB [dari] [sampai] [--min 1500]

Cek bab novel (file NNN.txt, baris pertama = judul) untuk bahasa tengah:
KATA (kurang dari batas minimal), DASH (tanda pisah panjang), AI (frasa khas tulisan mesin),
LISAN (kata gaul/Jakarta), KAKU (kata arkais/terlalu baku), TELAH (terlalu sering),
PENGHUBUNG (sama/pas/terus/tapi/kasih/bilang menumpuk). Keluar dengan kode 1 kalau ada masalah.
"""
import re, sys
from pathlib import Path

argv = sys.argv[1:]
MIN = 1500
if "--min" in argv:
    k = argv.index("--min"); MIN = int(argv[k + 1]); del argv[k:k + 2]
if not argv:
    sys.exit(__doc__)
B = Path(argv[0])
a = int(argv[1]) if len(argv) > 1 else 1
z = int(argv[2]) if len(argv) > 2 else 9999

LISAN = re.compile(r"\b(nggak|ngga|enggak|gak|udah|udahan|banget|kayak|kayaknya|aja|doang|emang|gitu|gini|gimana|bikin\w*|kelar|ngapain|sih|dong|deh|kok|nih|tuh|bener|beneran|gede|bareng|soalnya|makanya|lagian|barusan|nemu|nyari|ketemu|ngomong\w*|ngerti|mikir\w*|inget|seneng|capek|cape|abis|dateng|liat\w*|nungguin|cuma|kalo|ngeliat\w*|ngelihat\w*|nyopot\w*|copot\w*|bego|mampus)\b", re.I)
INV = re.compile(r"\b(?:nunggu\w*|duluan|pakein|di(?!ngin)\w{3,}(?:hin|kin|sin|pin|rin|nin|lin|tin|bin|win))\b", re.I)
PENGHUBUNG = re.compile(r"\b(sama|pas|terus|tapi|kasih|bilang\w*)\b", re.I)
NGNY = re.compile(r"\b(?:ng|ny)\w+", re.I)
NGOK = set("nyaris nyata nyatanya nyawa nyala nyalanya nyalakan nyaman nyamannya nyanyi nyanyian nyanyiannya nyanyikan nyanyianku nyonya nyamuk nyeri nyerinya nyenyak nyali nyalinya nyiur ngeri ngerinya ngilu ngarai nganga ngengat".split())
KAKU = re.compile(r"\b(tatkala|engkau|dikau|nan|adapun|hendak(?:lah)?|menyantap|bersantap|sesungguhnya|niscaya|sekonyong-konyong)\b", re.I)
AI = re.compile(r"tak terucap|menggantung di udara|tanpa sadar menahan napas|sesuatu dalam diriku berubah|bagaikan permadani|seolah dunia berhenti|waktu seakan berhenti|di saat itu juga", re.I)
DASH = re.compile("[—–―]|--+")
BAKU = {}
for _l in (Path(__file__).parent.parent / "data" / "baku-terpilih.csv").read_text(encoding="utf-8").splitlines()[1:]:
    _a, _b, _c = _l.split(";", 2)
    if _a != _b: BAKU[_a] = _b
TANAH_LIAT = re.compile(r"\btanah\s+liat\w*", re.I)

bad = tot = n = 0
for f in sorted(B.glob("[0-9]*.txt")):
    i = int(f.stem)
    if not a <= i <= z:
        continue
    s = f.read_text(encoding="utf-8")
    L = s.split("\n", 1)
    body = re.sub(r"</?em>", "", L[1] if len(L) > 1 else "")
    bodyl = TANAH_LIAT.sub("tanah", body)
    w = len(body.split()); tot += w; n += 1
    telah = len(re.findall(r"\btelah\b", body, re.I))
    p = []
    if w < MIN: p.append(f"KATA {w}")
    if DASH.search(s): p.append("DASH")
    if m := AI.findall(s): p.append(f"AI {m[:4]}")
    sl = LISAN.findall(bodyl) + INV.findall(body) + [x for x in NGNY.findall(body) if len(x) > 3 and x.lower() not in NGOK]
    if sl: p.append(f"LISAN {len(sl)} {sorted(set(x.lower() for x in sl))[:8]}")
    if m := KAKU.findall(body): p.append(f"KAKU {len(m)} {sorted(set(x.lower() for x in m))[:6]}")
    bk = [x for x in re.findall(r"[a-z]+", body.lower()) if x in BAKU]
    if bk: p.append(f"EJAAN {len(bk)} {sorted(set(x + '>' + BAKU[x] for x in bk))[:6]}")
    if telah > 8: p.append(f"TELAH {telah}")
    ph = PENGHUBUNG.findall(body)
    if len(ph) > 25: p.append(f"PENGHUBUNG {len(ph)} (cek sama/pas/terus/tapi)")
    if p:
        bad += 1
        print(f.stem, L[0].strip(), "|", " ; ".join(p))
print(f"bab {n} kata {tot} bermasalah {bad}")
sys.exit(1 if bad else 0)
