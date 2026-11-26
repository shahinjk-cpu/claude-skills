# Streams and I/O Reference

Guidelines for choosing between iostreams, buffered formatting, and dedicated parsers when performing input and output in C++.

---

## Performance & Buffering

- **Cost of Streams**: Standard iostreams are ergonomic for quick scripts or non-critical paths, but carry formatting, locale, and per-call overhead that makes them slow on hot paths.
- **Buffer and Write Once**: For high-throughput or latency-sensitive I/O, format data into an in-memory buffer first (for example with `std::format` or `std::to_chars`) and issue a single write operation instead of streaming small pieces repeatedly.
- **Disabling C Sync (`sync_with_stdio`)**: Calling `std::ios::sync_with_stdio(false)` only yields safe gains when C (`stdio.h` / `<cstdio>`) and C++ stream I/O are not interleaved on the same standard streams; mixing them without synchronization causes interleaved or unpredictable output.

---

## Input Parsing & Stream State

- **Avoid `operator>>` for Strict Formats**: Do not rely on `operator>>` when input structure, delimiters, or exact bounds must be validated—it skips leading whitespace by default and partially consumes malformed tokens.
- **Check State or Use a Dedicated Parser**: Inspect stream state (`fail()`, `bad()`, `eof()`) after every extraction when using streams, or prefer explicit token/character parsing (`std::from_chars`, `std::string_view` slicing, or a dedicated format parser) for strict validation.
