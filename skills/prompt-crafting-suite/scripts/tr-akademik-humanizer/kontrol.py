"""Orijinal ve yeniden yazılmış metin arasında sayı ve atıf kaybını/eklenmesini bulur.

Kullanım: python -I kontrol.py orijinal.txt yeni.txt
Çıkış kodu: 0 = temiz, 1 = fark var.
"""
import re
import sys
from collections import Counter

# 12 | 3,5 | 1.250 | %40 | 40% | 1-2 (aralıklar ayrı sayılar olarak yakalanır)
NUM = re.compile(r"%?\d+(?:[.,]\d+)*%?")
# (Kaya, 2022) (Kaya ve Demir, 2022) (Kaya vd., 2022a; Smith et al., 2021)
PAREN_CITE = re.compile(r"\(([^()]*?\b(?:19|20)\d{2}[a-z]?)\)")
# [12] [3-5] [1, 4]
BRACKET_CITE = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")


def extract(text):
    cites = Counter()
    for m in PAREN_CITE.finditer(text):
        for part in m.group(1).split(";"):
            cites[" ".join(part.split())] += 1
    for m in BRACKET_CITE.finditer(text):
        cites[re.sub(r"\s+", "", m.group(0))] += 1
    # Atıfların içindeki yılları sayı listesine tekrar katmamak için çıkar
    stripped = BRACKET_CITE.sub(" ", PAREN_CITE.sub(" ", text))
    nums = Counter(("%" if "%" in n else "") + n.replace("%", "").rstrip(".,")
                   for n in NUM.findall(stripped))
    return nums, cites


def report(label, old, new):
    missing, added = old - new, new - old
    for name, diff in (("KAYBOLAN", missing), ("YENİ EKLENEN", added)):
        for item, count in sorted(diff.items()):
            print(f"{name} {label}: {item}" + (f" (x{count})" if count > 1 else ""))
    return bool(missing or added)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    old_text, new_text = (open(p, encoding="utf-8").read() for p in sys.argv[1:])
    old_nums, old_cites = extract(old_text)
    new_nums, new_cites = extract(new_text)
    dirty = report("sayı", old_nums, new_nums) | report("atıf", old_cites, new_cites)
    print("FARK VAR" if dirty else "TEMİZ: sayılar ve atıflar aynı.")
    sys.exit(1 if dirty else 0)


if __name__ == "__main__":
    main()
