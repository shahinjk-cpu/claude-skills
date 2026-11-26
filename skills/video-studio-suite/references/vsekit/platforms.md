# Platform specs (check the platform's current docs when it matters — these drift)

## YouTube (long-form)
- 16:9, 1920×1080 (or 3840×2160), 24/25/30/50/60 fps — keep the source fps; H.264 High, AAC 48 kHz.
- Loudness: YouTube normalises down to about −14 LUFS; master to −14 LUFS, true peak ≤ −1 dBTP.
- Thumbnail: 1280×720 (16:9), min width 640; keep the file small (≤ 2 MB is the long-standing safe limit).
  Big readable face/object + ≤ 4 words; test at 168×94 (search size).
- Chapters: timestamps in the description, first one `0:00`, at least 3, each ≥ 10 s long.
- Captions: upload `.srt` (`transcribe.to_srt`) — better than auto-captions, also indexed for search.
- Retention basics: hook in the first 5–8 s; analyse references with `vsekit.analyze` for cuts/min and wpm.

## YouTube Shorts / TikTok / Instagram Reels
- 9:16, 1080×1920, 30 or 60 fps.
- Length: Shorts up to 3 min; TikTok/Reels allow longer, but short + loopable performs best for new channels.
- Safe zone for text: avoid the bottom ~20 % (caption/description UI) and the right ~15 % (buttons);
  top ~10 % holds the progress/search bar. Captions around y ≈ 1150–1350 of 1920 work well.
- Hook text on screen in the first 1–2 s; burned-in captions (most people watch muted).
- −14 LUFS is a good universal master.

## Web portals / itch.io trailers
- 16:9 1920×1080, 15–30 s gameplay-first; first frame must already show the game.
- Keep files small for page embeds: `hevc_nvenc` or x264 CRF 23.

## Licences for music/footage
- CC BY: allowed with visible credit (title, author, source, licence) — put it in the video and description.
- CC BY-NC: no monetised use. "No copyright sounds" claims ≠ licence; check the actual terms.
- NASA media: generally not copyrighted (no endorsement implied; some items carry third-party rights).
- yt-dlp metadata `license` = "Creative Commons Attribution license (reuse allowed)" or empty/standard.
