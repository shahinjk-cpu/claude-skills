# meta-ads spec v1 — the `ads.json` format

This document is the contract between you (an agent holding ad information in whatever form: a spreadsheet, an Excel file, an Ad Library page, notes, a brief) and the meta-ads renderer. Read it, then write an `ads.json` yourself. The skill never reads your sources or converts anything; it only checks and renders a file in this format.

Contents: [1 Workflow](#1-workflow) · [2 File](#2-file-and-paths) · [3 Top level](#3-top-level) · [4 brands](#4-brands) · [5 media](#5-media) · [6 ads](#6-ads) · [7 Rules](#7-rules-that-matter) · [8 Placements](#8-placements) · [9 CTA codes](#9-cta-codes) · [10 Glossary](#10-field-glossary-for-common-sources) · [11 Examples](#11-examples) · [12 Check output](#12-reading-checkpy-output)

## 1. Workflow

`<skill-dir>` below is the folder that contains this SPEC.md and SKILL.md.

1. Write `ads.json` and make sure every media file it points to exists on disk. Normally it lives in a library, `meta-ads/<library>/ads.json` with media in `meta-ads/<library>/assets/` (create one with `python <skill-dir>/scripts/library.py new "Name"`; SKILL.md has the layout). Anywhere else works for one-off renders.
2. `python <skill-dir>/scripts/check.py ads.json`. Fix every **error**; read the **warnings** and the **unlock** list.
3. Decide with the user whether to supply missing items (copy, creative ratios, avatar) or render with placeholders as-is.
4. `python <skill-dir>/scripts/render.py ads.json` writes the viewer to `<library>/viewer/` for a library spec, otherwise to `./meta-ads-output/<campaign>-<date>/` in your current working directory.
5. Optional: `python <skill-dir>/scripts/export_png.py <that folder>` for PNGs.

## 2. File and paths

- UTF-8 JSON. `spec_version` must be `1`.
- File paths inside the spec are **relative to `ads.json`**, or absolute.
- Unknown fields produce a warning and are ignored. `source` and `notes` are free-form anywhere they are allowed; nothing reads them except the viewer, which displays them.

## 3. Top level

| Field | Required | Meaning |
|---|---|---|
| `spec_version` | yes | `1` |
| `campaign` | yes | `{ "name": "...", "notes": "..." }`. `name` is the viewer title and, in a library, the library's display name (otherwise it also names the dated output folder). |
| `brands` | yes, ≥1 | Map of brand ID → identity (§4). The first brand is the default for ads that don't name one. |
| `media` | yes | Map of media ID → one image, video or placeholder (§5). May be `{}` only if every ad is invalid, so in practice ≥1. |
| `defaults` | no | Any ad field except `id`, `label`, `source`, `notes`. Applied to every ad that omits that field. Good for `cta`, `destination_url`, `engagement`, `brand`. |
| `ads` | yes, ≥1 | List of ads (§6). |

## 4. `brands`

```json
"brands": {
  "b_main":  { "page_name": "Northstep Shoes", "avatar": "m_logo", "ig_handle": "northstep", "verified": false },
  "b_rival": { "page_name": "Rival Runners", "avatar": "m_rival_logo_ph", "ig_handle": "rivalrunners" }
}
```
with, in `media`:
```json
"m_logo":          { "kind": "image", "src": "assets/northstep_logo.png" },
"m_rival_logo_ph": { "kind": "placeholder", "ratio": "1:1", "label": "Rival Runners logo", "color": "#1d2b3a" }
```

| Field | Required | Meaning |
|---|---|---|
| `page_name` | yes | Facebook Page name as shown on ads. Missing → "Your Brand" (flagged). |
| `avatar` | **yes** | Media ID of the page's profile picture, **or** of a `placeholder` when you don't have it. A placeholder avatar renders as an initials circle in the placeholder's `color` and keeps the mockups "simulated" until replaced. Omitting `avatar` is an error. |
| `ig_handle` | no | Instagram username without `@`. Missing → derived from page name (flagged). |
| `ig_avatar` | no | Separate Instagram profile picture (media ID). Defaults to `avatar`. |
| `verified` | no | `true` shows the blue verified badge. |

**Getting the avatar.** The profile picture is in every ad's header, so look for it before falling back to a placeholder:
- your own brand: the logo or profile image the user has;
- an Ad Library export: a field such as `page_profile_picture_url` (Meta CDN links expire, so download it right away);
- a public Facebook Page: `https://graph.facebook.com/<page-username>/picture?type=large` redirects to the current profile picture (about 480 px, no login needed).

Save the file locally and reference it as an `image` media entry. Only if none of these work, create a `placeholder` avatar (ratio `1:1`, a `label` naming the logo, and the brand's main colour as `color` if known). The initials come from each brand's `page_name`, so one placeholder per brand keeps the shopping list clear.

Several brands let you put competitor ads beside your own in the Compare ads view; give each ad `"brand": "<id>"`.

## 5. `media`

Every unique file appears **once**, under an ID of your choosing. Ads refer to media by ID. If 100 ads use one picture, it is listed once and referenced 100 times.

```json
"media": {
  "m_logo":   { "kind": "image", "src": "assets/logo.png" },
  "m_hero":   { "kind": "image", "src": "assets/hero_4x5.jpg", "label": "Hero shot, model on trail" },
  "m_teaser": { "kind": "video", "src": "assets/teaser.mp4", "poster": "assets/teaser_cover.jpg" },
  "m_idea1":  { "kind": "placeholder", "ratio": "1:1", "label": "Close-up of the sole in a puddle" }
}
```

| Field | Applies to | Meaning |
|---|---|---|
| `kind` | all | `image`, `video` or `placeholder` |
| `src` | image, video | Path to the file (jpg/png/webp/gif; mp4/mov/webm). An `http(s)` URL is accepted and downloaded once at render time, but **Meta CDN URLs (fbcdn, scontent) expire within days**: save files locally when you collect them. |
| `poster` | video | Optional cover image. Without it a frame is extracted with ffmpeg. |
| `ratio` | placeholder (required); others optional | `"1:1"`, `"4:5"`, `"9:16"`, `"1.91:1"`, `"16:9"`, `"2:3"` or any `"W:H"`. For real files the measured size always wins; a declared ratio that disagrees produces a warning. |
| `label` | all | Human description. For placeholders it is printed inside the frame, so describe the intended image. |
| `color` | placeholder | Optional background colour of the placeholder frame, e.g. `"#2f3e46"`. |

**Placeholders** stand in for creative that doesn't exist yet. Every other part of the mockup (copy, truncation, CTA, engagement bar, platform UI) renders exactly, so copy can be judged before any photo or video is made. When a file becomes available, change that one entry to `{"kind": "image", "src": ...}`; every ad using the ID updates.

## 6. `ads`

```json
{
  "id": "A1",
  "label": "Hook: discount first",
  "group": "Fall hero headlines",
  "brand": "b_main",
  "format": "image",
  "primary_text": "Our fall collection just dropped 🍂\nUp to 40% off for launch week only.",
  "headline": "Up to 40% off fall styles",
  "description": "Free returns on every order",
  "cta": "SHOP_NOW",
  "display_link": "northstep.com",
  "destination_url": "https://northstep.com/fall",
  "creative": { "4:5": "m_hero", "1:1": "m_hero_sq", "9:16": "m_hero_tall" },
  "engagement": { "reactions": 412, "comments": 38, "shares": 17, "likes": 2304, "views": 26100 },
  "placements": "auto",
  "source": { "sheet_row": 7 },
  "notes": "Variant from the Nov brief"
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Unique; letters, digits, `_ - .`; max 40 chars. Used in file names. |
| `label` | no | Short human name shown in the viewer. |
| `group` | no | Ads sharing a group are compared together (e.g. one image, five headlines). |
| `brand` | no | Brand ID; default is the first brand. |
| `format` | yes | `image`, `video` or `carousel`. A video ad may use a `placeholder` while the video doesn't exist yet. |
| `primary_text` | no (warned) | The main text above the media (FB) / caption (IG). Exact text: keep line breaks as `\n`, emoji as-is. |
| `headline` | no | The bold line in the link area. |
| `description` | no | The line under the headline; only some placements show it. |
| `cta` | no | A code from §9, e.g. `"SHOP_NOW"`. `null` = no button. If omitted: no button plus a warning. |
| `display_link` | no | Link text shown in the link area. Default: the domain of `destination_url`. |
| `destination_url` | no | Landing page. |
| `creative` | image/video: yes | Map of ratio → media ID. Give every version you have; the renderer picks the best fit per placement. Keys should be the ratio of the file; the measured ratio is what counts. |
| `cards` | carousel: yes | 2–10 cards (§6.1). |
| `engagement` | no | Counts shown on the mockup: `reactions` (FB), `comments`, `shares`, `likes` (IG), `views` (video). Defaults are realistic mid-size numbers. |
| `placements` | no | `"auto"` (all), a list of placement IDs (§8), or `{ "exclude": [ ... ] }`. |
| `source` | no | Free-form provenance: sheet row, Ad Library ID, file name. |
| `notes` | no | Free text. |

### 6.1 Carousel cards

```json
"format": "carousel",
"primary_text": "One brand, every kind of walk.",
"cta": "SHOP_NOW",
"cards": [
  { "creative": { "1:1": "m_trail" }, "headline": "Trail Runner", "description": "From $129", "destination_url": "https://…/trail" },
  { "creative": { "1:1": "m_city" },  "headline": "City Sneaker", "description": "From $99", "cta": "LEARN_MORE" }
]
```

Card fields: `creative` (required, same shape as an ad's), `headline`, `description`, `destination_url`, `display_link`, `cta` (defaults to the ad's). Keep card ratios consistent; Meta recommends 1:1 (4:5 works for image-only Instagram carousels).

## 7. Rules that matter

1. **Don't invent.** If a value is unknown, leave the field out. `check.py` reports the gap and the mockup shows a visible placeholder. A made-up headline looks real in a mockup and misleads whoever reviews it.
2. **One media entry per unique file.** Reuse the ID. (The renderer also fingerprints files and stores identical content once, and `check.py` warns about duplicates and near-duplicates, but listing once keeps the spec honest and the unlock list accurate.)
3. **Copy is verbatim.** Don't trim to fit; the mockup shows the real truncation, which is the point.
4. **List every ratio you have** for each ad's creative. The renderer chooses per placement; missing ratios become "simulated" mockups plus an unlock suggestion.
5. **Local files over URLs.** Download media while you still can.
6. **One ad = one thing a person would see.** Variants are separate ads; tie them together with `group`.
7. **Every brand has an avatar: the real one or a placeholder.** The profile picture sits at the top of every placement, so a wrong or missing one changes the whole mockup. Find the real picture first (§4); if you can't, create a placeholder avatar explicitly so the gap is visible in `check.py`'s unlock list instead of silently defaulted.

## 8. Placements

Placement IDs for `placements` and what each accepts. Mockup behaviour when a ratio doesn't fit: **pad** = frame at the nearest supported ratio with the whole image inside and gray bars (Facebook placements); **crop** = cut to the nearest supported ratio (Instagram Feed and Explore); **fill** = shown smaller on a blurred background (Meta pads automatically; padding style is approximated); **letterbox** = black bars. Rules come from `assets/placements.json` (dated; see `references/placements.md` for sources).

<!-- BEGIN:placements (generated by scripts/sync_spec.py; do not edit by hand) -->
| ID | Placement | Formats | Media fit | Primary text | Headline | Description | Safe zone |
|---|---|---|---|---|---|---|---|
| `fb_feed_mobile` | Facebook Feed (mobile) | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else pad<br>video: 4:5 – 1.91:1 native (ideal 4:5); else pad<br>carousel: 1:1 native (ideal 1:1); else pad | ≤125 rec., 3 lines then “… See more” | ≤27 rec. | ≤30 rec., 2 lines then “…” | – |
| `fb_feed_desktop` | Facebook Feed (desktop) | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else pad<br>video: 1:1 – 1.91:1 native (ideal 1:1); else letterbox<br>carousel: 1:1 native (ideal 1:1); else pad | ≤125 rec., 3 lines then “… See more” | ≤27 rec. | ≤30 rec., 2 lines then “…” | – |
| `fb_stories` | Facebook Stories | image, video, carousel | 9:16 native (ideal 9:16); else fill | ≤125 rec., 3 lines then “… more” | not shown | not shown | top 14%, bottom 35%, sides 6% |
| `fb_reels` | Facebook Reels | image, video, carousel | 9:16 native (ideal 9:16); else fill | ≤40 rec., 2 lines then “… more” | ≤55 rec. | not shown | top 14%, bottom 35%, sides 6% |
| `fb_marketplace` | Facebook Marketplace | image, video, carousel | 1:1 native (ideal 1:1); else pad | not shown | ≤40 rec. | not shown | – |
| `fb_video_feeds` | Facebook Video Feeds | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else pad<br>video: 4:5 – 1.91:1 native (ideal 4:5); else pad<br>carousel: 1:1 native (ideal 1:1); else pad | ≤125 rec., 3 lines then “… See more” | ≤27 rec. | ≤30 rec., 2 lines then “…” | – |
| `fb_instream` | Facebook In-stream video | image, video, carousel | 1:1 – 1.91:1 native (ideal 16:9); else letterbox | not shown | ≤40 rec. | not shown | – |
| `fb_right_column` | Facebook Right Column | image, video, carousel | 1:1 – 1.91:1 native (ideal 1:1); else pad | not shown | ≤40 rec. | not shown | – |
| `fb_search` | Facebook Search results | image, video, carousel | image: 1:1 – 1.91:1 native (ideal 1:1); else pad<br>video: 1:1 native (ideal 1:1); else pad<br>carousel: 1:1 native (ideal 1:1); else pad | ≤125 rec., 3 lines then “… See more” | ≤40 rec. | ≤30 rec., 2 lines then “…” | – |
| `ig_feed` | Instagram Feed | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else crop<br>video: 9:16 – 1.91:1 native (ideal 9:16); else crop<br>carousel: 4:5 – 1:1 native (ideal 4:5); else crop | ≤125 rec., 2 lines then “… more” | not shown | not shown | – |
| `ig_stories` | Instagram Stories | image, video, carousel | 9:16 native (ideal 9:16); else fill | ≤125 rec., 3 lines then “… more” | not shown | not shown | top 14%, bottom 35%, sides 6% |
| `ig_reels` | Instagram Reels | image, video, carousel | 9:16 native (ideal 9:16); else fill | ≤44 rec., 2 lines then “… more” | not shown | not shown | top 14%, bottom 35%, sides 6% |
| `ig_explore` | Instagram Explore (opened post) | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else crop<br>video: 9:16 – 1.91:1 native (ideal 9:16); else crop<br>carousel: 4:5 – 1:1 native (ideal 4:5); else crop | ≤125 rec., 2 lines then “… more” | not shown | not shown | – |
| `ig_explore_home` | Instagram Explore Home (grid) | image, video, carousel | image: 4:5 native (ideal 4:5); else crop<br>video: 9:16 – 4:5 native (ideal 9:16); else crop<br>carousel: 4:5 native (ideal 4:5); else crop | not shown | not shown | not shown | – |
| `ig_profile_feed` | Instagram Profile Feed | image, video, carousel | image: 4:5 – 1.91:1 native (ideal 4:5); else crop<br>video: 9:16 – 1.91:1 native (ideal 9:16); else crop<br>carousel: 4:5 – 1:1 native (ideal 4:5); else crop | ≤125 rec., 2 lines then “… more” | not shown | not shown | – |
<!-- END:placements -->

## 9. CTA codes

<!-- BEGIN:cta (generated by scripts/sync_spec.py; do not edit by hand) -->
| Code | Button label |
|---|---|
| `LEARN_MORE` | Learn more |
| `SHOP_NOW` | Shop now |
| `SIGN_UP` | Sign up |
| `BOOK_NOW` | Book now |
| `BOOK_TRAVEL` | Book travel |
| `APPLY_NOW` | Apply now |
| `BUY_TICKETS` | Buy tickets |
| `CALL_NOW` | Call now |
| `CONTACT_US` | Contact us |
| `DONATE_NOW` | Donate now |
| `DOWNLOAD` | Download |
| `GET_DIRECTIONS` | Get directions |
| `GET_OFFER` | Get offer |
| `GET_QUOTE` | Get quote |
| `GET_SHOWTIMES` | Get showtimes |
| `GET_PROMOTIONS` | Get promotions |
| `LIKE_PAGE` | Like Page |
| `LISTEN_NOW` | Listen now |
| `LISTEN_MUSIC` | Listen now |
| `OPEN_LINK` | Open link |
| `ORDER_NOW` | Order now |
| `PLAY_GAME` | Play game |
| `REQUEST_TIME` | Request time |
| `SUBSCRIBE` | Subscribe |
| `USE_APP` | Use app |
| `USE_MOBILE_APP` | Use app |
| `WATCH_MORE` | Watch more |
| `INSTALL_MOBILE_APP` | Install now |
| `INSTALL_APP` | Install now |
| `MESSAGE_PAGE` | Send message |
| `WHATSAPP_MESSAGE` | Send WhatsApp message |
| `BUY_NOW` | Buy now |
| `GET_STARTED` | Get started |
| `SEE_MORE` | See more |
| `SEE_DETAILS` | See details |
| `WATCH_VIDEO` | Watch video |
| `WATCH_NOW` | Watch now |
| `CHAT_NOW` | Chat now |
| `ADD_TO_CART` | Add to cart |
| `VIEW_PRODUCT` | View product |
| `SEE_SHOP` | See shop |
| `NO_BUTTON` | (no button) |
<!-- END:cta -->

Use the code (left column). A label such as `"Shop now"` is accepted with a warning. `NO_BUTTON` or `null` = no button.

## 10. Field glossary for common sources

Names you'll meet in source data, and the spec field they most likely mean. Use judgment; these are hints, not rules.

| Source wording | Spec field |
|---|---|
| Body, Primary text, Ad text, Copy, Caption, Message, Post text | `primary_text` |
| Title, Headline, Link title | `headline` (single image/video) or card `headline` (carousel) |
| Link description, Description, News feed link description | `description` |
| Call to action, CTA, Button | `cta` (map the label to a code in §9) |
| Link, Website URL, Destination, Landing page | `destination_url` |
| Display link, Caption (Ads Manager), Display URL | `display_link` |
| Image, Image file, Image hash, Creative, Asset, Thumbnail | a `media` entry + `creative` reference |
| Video, Video file, Video ID | a `media` entry of kind `video` |
| Page, Page name, Advertiser, Brand | `brands.*.page_name` |
| Instagram account, IG handle | `brands.*.ig_handle` |
| Ad name, Ad set name, Variant | `label` and/or `group` |
| Library ID, Ad ID, Started running on, Platforms | `source` |
| Image idea, Concept, Visual direction (no file yet) | a `placeholder` media entry with that text as `label` |

Spreadsheets often repeat the same image name or URL on many rows; that is one media entry referenced by many ads. Embedded spreadsheet images that are byte-identical or visually identical are also one media entry.

## 11. Examples

Complete, valid files live in `assets/examples/`:

- `showcase.json`: every format (image variants in a group, video, carousel, 1.91:1-only banner, a copy-first placeholder ad, a competitor brand).
- `copy-first.json`: no creative files at all; several ads share placeholders.

Smallest valid file:

```json
{
  "spec_version": 1,
  "campaign": { "name": "Quick test" },
  "brands": { "b": { "page_name": "Acme", "avatar": "m_logo" } },
  "media": {
    "m_logo": { "kind": "placeholder", "ratio": "1:1", "label": "Acme logo", "color": "#c0392b" },
    "m1": { "kind": "placeholder", "ratio": "4:5", "label": "Product on white" }
  },
  "ads": [ { "id": "A1", "format": "image", "primary_text": "Hello", "headline": "Try Acme", "cta": "LEARN_MORE", "creative": { "4:5": "m1" } } ]
}
```

## 12. Reading `check.py` output

`check.py` writes `inventory.json` (for you) and `inventory.md` (for people) and exits 1 if there are errors.

- `errors`: must fix before rendering (`where` points at the field, e.g. `ads[A3].creative.9:16`).
- `warnings`: renderable, but worth a look (missing copy, unknown fields, low resolution, duplicate media).
- `matrix[ad][placement].status`: `actual` (native fit, real creative), `simulated` (renders with a fallback or placeholder; `reasons` says why), `not_eligible` (format can't run there), `excluded` (by the ad's `placements`).
- `unlock`: what to add next, ranked by how many mockups it improves, e.g. "Add a 9:16 version of m_hero → 12 mockups become native".
- `shopping_list`: every placeholder, what it should show, and the ratios needed to cover all placements.

Act on `unlock` and `shopping_list` by asking the user, not by guessing.
