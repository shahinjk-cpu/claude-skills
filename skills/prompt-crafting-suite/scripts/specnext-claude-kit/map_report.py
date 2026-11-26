#!/usr/bin/env python3
"""Rank a z88dk linker map by symbol size, area by area, and flag library code the source never names.

    python map_report.py app.map                    # every area, the 25 biggest symbols of each
    python map_report.py app.map --top 40 --area PAGE_20
    python map_report.py app.map --org 0x8000 --fence 0xFDFB    # adds the main area's free bytes to the fence

A z88dk map (zcc -m) holds one line per symbol:  name = $ADDR ; addr, scope, , module, section, file:line
It carries addresses, not sizes, so a symbol's size is taken as the gap to the next symbol of the same area. The
figure includes any literals the compiler placed behind the symbol, and the last symbol of an area has no figure.
Only "addr" lines count: "const" lines are numbers, not storage.

An area is a banked section (PAGE_nn or BANK_nn, whose addresses overlap other pages) or "main" (everything else).
Standard library only.
"""

import argparse
import re
import sys

LINE = re.compile(r"^(\w+)\s*=\s*\$([0-9A-Fa-f]+)\s*;\s*addr\b(.*)$")
BANKED = re.compile(r"^(PAGE|BANK)_\d+", re.IGNORECASE)

# Library code worth questioning. Not waste by itself: printf brings its formatter in for a reason.
PASSENGERS = [
    (re.compile(r"^__array_at|^_ioctl|^__?zx_01_output|console|terminal"),
     "console / terminal driver: try -startup=31 if the program never prints through stdio"),
    (re.compile(r"^__?printf|^__?sprintf|^_vfprintf|^__?fputc|_stdio"),
     "stdio / printf: avoid printf, and set CLIB_STDIO_HEAP_SIZE = 0 if no file is opened through stdio"),
    (re.compile(r"^__?malloc|^__?heap|_sbrk"),
     "the heap: set CLIB_MALLOC_HEAP_SIZE = 0 if the program never allocates"),
    (re.compile(r"^__?mul(long|longlong)|^__?div(s|u)long|^__?float|^__?fs"),
     "32-bit or float helpers: use 16-bit types where the values fit"),
]


def number(text):
    return int(text, 0)


def read_map(path):
    areas = {}
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = LINE.match(line)
            if not match:
                continue
            fields = [field.strip() for field in match.group(3).split(",")]
            section = fields[4] if len(fields) > 4 else ""
            area = section if BANKED.match(section) else "main"
            areas.setdefault(area, []).append((int(match.group(2), 16), match.group(1)))
    return areas


def sized(symbols):
    ordered = sorted(symbols)
    return [(ordered[i + 1][0] - ordered[i][0], ordered[i][0], ordered[i][1]) for i in range(len(ordered) - 1)]


def passenger(name):
    for pattern, hint in PASSENGERS:
        if pattern.search(name):
            return hint
    return None


def main():
    parser = argparse.ArgumentParser(description="Rank a z88dk .map by symbol size, area by area.")
    parser.add_argument("map")
    parser.add_argument("--top", type=int, default=25, help="symbols listed per area (default 25)")
    parser.add_argument("--area", help="only this area: main, or a section name such as PAGE_20")
    parser.add_argument("--org", type=number, help="first address of the main area, for the free-bytes line")
    parser.add_argument("--fence", type=number, help="last address the main area may reach (the stack fence)")
    args = parser.parse_args()

    areas = read_map(args.map)
    if sum(len(symbols) for symbols in areas.values()) < 2:
        sys.exit("map_report.py: no 'name = $ADDR ; addr' lines found: is this a z88dk map (zcc -m)?")
    if args.area and args.area not in areas:
        sys.exit("map_report.py: no area %r; the map has: %s" % (args.area, ", ".join(sorted(areas))))

    totals = {}
    for area in sorted(areas, key=lambda name: (name != "main", name)):
        if args.area and area != args.area:
            continue
        symbols = areas[area]
        if area == "main" and args.org is not None and args.fence is not None:
            symbols = [symbol for symbol in symbols if args.org <= symbol[0] <= args.fence]
        rows = sized(symbols)
        print("\n== %s: %d symbols ==" % (area, len(symbols)))
        print("%6s  %-6s  %s" % ("BYTES", "ADDR", "SYMBOL"))
        for size, address, name in sorted(rows, reverse=True)[:args.top]:
            print("%6d  0x%04X  %s%s" % (size, address, name, "   <-- library" if passenger(name) else ""))
        for size, _, name in rows:
            hint = passenger(name)
            if hint:
                count, total = totals.get(hint, (0, 0))
                totals[hint] = (count + 1, total + size)
        if area == "main" and symbols and args.org is not None and args.fence is not None:
            highest = max(symbols)[0]
            print("free: highest symbol 0x%04X, %d bytes to the fence 0x%04X (the build's own figure wins)"
                  % (highest, args.fence - highest, args.fence))

    print()
    if totals:
        for hint, (count, total) in sorted(totals.items(), key=lambda item: -item[1][1]):
            print("~%5d bytes in %2d symbol(s): %s" % (total, count, hint))
    else:
        print("No known library passengers found.")


if __name__ == "__main__":
    main()
