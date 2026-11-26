---
name: z88dk-map-room
description: Find where the bytes of a z88dk program go before optimising your own code - rank the linker .map by symbol size in the main bank and in each banked page, spot library code the source never names (the ZX terminal driver, stdio, the heap, 32-bit math helpers), drop the console with -startup=31 and the heap pragmas, and read room figures without being fooled (room that only moved between the stack and statics, big structs as locals under zsdcc). Use this skill whenever a z88dk build is short of room, a page or the main bank overflows, or the user asks what is big, where the bytes went, why the binary is so large or how to free bytes, even if they only say "we are out of room".
---

# Where the bytes go in a z88dk program

Rank the map before you optimise your own code. In the application this comes from, ten releases shipped with about
3.3 KB of console driver nobody had asked for; it was found the first time the map was sorted by size.

## Rank the map
`python ${CLAUDE_SKILL_DIR}/scripts/map_report.py <app.map>` reads the map `zcc -m` writes and prints, for the main
area and for each banked section (`PAGE_nn`, `BANK_nn`), the biggest symbols, then the library code it recognised:

- `--top 40` lists more symbols; `--area PAGE_20` (or `--area main`) keeps one area.
- `--org 0x8000 --fence 0xFDFB` adds the main area's free bytes up to the stack fence. The build script's own room
  figure stays the authority; this line is a cross-check.
- A z88dk map holds addresses, not sizes. A symbol's figure is the gap to the next symbol of its area, so it includes
  literals the compiler placed behind it, and the last symbol of an area has no figure. It answers "what is big, and
  did I write it?", not "exactly how many bytes".
- Only the map's `addr` lines are storage. Its `const` lines are numbers (configuration values, sizes): never size them.

## Library code your source never names
| In the map | What it is | What to try |
|---|---|---|
| `__array_at`, `_ioctl_*`, `zx_01_output_*`, names with `console` or `terminal` | the ZX terminal driver and its font | `-startup=31` (below) |
| `__printf*`, `_vfprintf`, `_fputc`, `*_stdio*` | stdio and the printf formatter | no `printf`; `CLIB_STDIO_HEAP_SIZE = 0` |
| `_malloc*`, `__heap*`, `_sbrk` | the heap | `CLIB_MALLOC_HEAP_SIZE = 0` if nothing allocates |
| `__mullong`, `__divulong`, `__divslong`, `__fs*` | 32-bit and float helpers | 16-bit types where the values fit |

A hit is a question, not a verdict: a program that prints needs its formatter.

## The no-console startup: `-startup=31`
A `+zxn` program linked with a console startup (`-startup=0` in the measured project) carries the terminal driver, the
stdio console plumbing and the driver's own copy of the font, so that `printf` can write to a Spectrum screen. A
program that draws its own screen (Layer 2, sprites, a tilemap) and does its file I/O through esxDOS calls never uses
them.

- `zcc +zxn -startup=31 ...` selects the CRT with no console driver and no stdio device table. The CRT itself, esxDOS
  calls, interrupts and the stack layout are unchanged.
- **Measured** in one application's main bank: free room went from 279 to 3 592 bytes (about 3.3 KB), by the build's
  own room figure. The two biggest symbols of the old map were `__array_at` (1 085 bytes) and `_ioctl_get_delay`
  (584 bytes), neither named anywhere in the source.
- What you give up: `printf`, `puts`, `putchar` and `gets` still link but have nowhere to go. Keep a debug flavour on
  the console startup if you print to the screen while debugging.
- The pragmas that go with it, for a program that never allocates and opens no stdio file:

  ```c
  #pragma output CRT_ENABLE_CLOSE      = 0
  #pragma output CLIB_MALLOC_HEAP_SIZE = 0
  #pragma output CLIB_STDIO_HEAP_SIZE  = 0
  #pragma output CLIB_FOPEN_MAX        = -1
  ```

- Check it: build, rank the map, switch the startup, rebuild and compare the room figure. Then start the program once
  on the emulator: a wrong device model shows at once, as a start that never reaches the first screen.

## Reading room figures without being fooled
- **Room that only moved.** In a program whose main bank's free bytes are also its C stack, moving a variable from a
  stack frame to a static lowers the "free" figure and saves the same bytes at run time. Measured: a change made the
  figure fall by 260 bytes (2 052 to 1 792) while the worst-case cost was 4 bytes, because 256 bytes had moved from
  two live stack frames into statics. Do that arithmetic before chasing a room warning.
- **Big structs as locals (zsdcc).** zsdcc reaches a function's locals through `(ix+d)`, and `d` is a signed byte. A
  local of 128 bytes or more pushes the function's other locals out of that reach, and every access to them grows.
  Measured: a 128-byte struct held as a local in five functions of one page cost that page about 115 bytes; as file
  statics, the page ended with more room than before the struct had grown (9 to 60 bytes free in one flavour, 83 to
  140 in another). A static is not re-entrant: when one of the functions can run inside another, give each its own.
- **Every flavour.** The same change costs different bytes in each build flavour; the tightest one decides.
- **Check the toolchain first.** A page that overflows on unmodified sources is the compiler, not the code: see the
  toolchain notes in the `zxnext-build` skill.

## What to report
The areas ranked, the library code found with its bytes, each change with the room before and after in the main bank
and in every page it touched (from the build's own figures), and what was given up (for example `printf`).

## Additional resources
- `scripts/map_report.py`: the map ranking described above (Python 3, standard library only).
- The `zxnext-banked-code` skill: moving a module into a page to free the main bank, safely.
