---
name: asset-hunter
description: Find, licence-check and download real photos, 3D assets, HDRIs, footage and animation clips for a documentary or video build, and record every file's licence and credit. Use whenever a video needs photos (Rockstar, Dundee, people, places), props, buildings, cars, characters, motion clips (Mixamo) or textures, or when the user says "get the assets", "find real photos", "download resources", "asset hunt".
---

# asset-hunter

Goal: every asset in a video is real, free-to-use now, and carries a licence line. Paid upgrades come later and need the owner's OK.

## Steps
1. List the shots and what each needs (photo, 3D prop, motion, footage). Facts only from the episode `sources.csv` (no CHECK/RUMOUR rows).
2. Search the right source (table below). Never use game footage, trailers, game screenshots, or NC/ND licences.
3. Download, then write a credit line: `Author, Licence, Source (title)` into the item's `props.source` and `assets.json`.
4. Look at every image before using it (Read the file or a contact sheet).
5. Report: file list + licence per file + anything rejected and why.

## Sources
| Need | Source | Licence | How |
|---|---|---|---|
| Photos, archive | Wikimedia Commons | PD / CC0 / CC-BY / CC-BY-SA (credit; flag SA to owner) | `node scripts/asset-hunter/commons.mjs "<query>"` then `get "<File:Name>" <out.jpg> [width]`. It rejects NC/ND. Wait ~6 s between calls (rate limit). |
| HDRI, textures, props | Poly Haven, ambientCG | CC0 | direct download links, list in `assets3d/CREDITS.md` |
| Characters + motion | Mixamo (Adobe login in Brave) | royalty-free incl. commercial video (Adobe FAQ, checked 26 Nov 2026) | playwright-cli on the `mybrave` session; X/Y Bot, In-Place clips |
| Models | Sketchfab | CC0 / CC-BY only | reject anything tagged game, studio or car brand (rips are often mislabelled) |
| Footage | Pexels, Pixabay | site licence | note URL + author |
| Voice | ElevenLabs | free tier non-commercial; paid before monetising | edge-tts is demo only |

Licence terms change: open the source's terms page once per project and cite its URL in the credits.

## Rules
- Reserved for the owner: what to buy, any paid subscription, final choice between look-alike options.
- Output: `public/images/<episode>/`, `assets3d/`, credits in `credits.jsonl` + `assets.json`. No absolute paths in scripts; Blender exe from env `BLENDER`.
- Rate limits: back off and retry; never hammer an API.
