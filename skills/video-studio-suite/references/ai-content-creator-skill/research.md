# Research playbook

## Query bank

Put the current date in every query, in the form `November 25, 2026` or `2026-11-25`. Run independent searches together. If a search returns nothing useful, change the wording rather than inventing results.

YouTube Shorts:

- `most viewed YouTube Shorts this week <date> viral topics views per day`
- `YouTube Shorts trending <date> fastest growing views`
- `site:scrollsonar.com/trends/youtube-shorts`
- `site:cutmarketing.app/trends short video trends this week`
- `trending YouTube Shorts hashtags <date> views`
- `YouTube Shorts trend report <date>`
- `animated cartoon YouTube Shorts trending <date> views` (cartoon-ready scope)

Facebook Reels:

- `Facebook Reels viral trends <date> most viewed`
- `Facebook Reels trending formats <date> viral reels`
- `Facebook Reels trend report <date> views`
- `viral Facebook Reels topics <date> roundup`

Cross-platform and format patterns:

- `TikTok and YouTube Shorts trends this week <date>`
- `viral short video formats <date> ranked list relatable split challenge`
- `trending hashtags short videos <date> views growth`
- `TikTok Creative Center trending videos <date>`

Animation and explainer queries — run **at least two** of these on every research pass, in addition to the platform queries above. They exist because generic "viral shorts" searches are dominated by realistic AI-human clips:

- `animated cartoon YouTube Shorts trending <date> views`
- `viral animation shorts <date> most viewed cartoon clip`
- `2D animation short video trend <date> views`
- `explainer animation viral short video <date>`
- `motion graphics explainer shorts trending <date>`
- `stop motion short viral <date> YouTube Shorts`
- `animated explainer TikTok trend <date> views`
- `viral animated short film roundup <date>`
- `animation short video chart <date> views growth`

AI-human detection query — run once, **only** to identify what must be excluded:

- `AI generated realistic human short video trend <date>` (results are candidates for the dropped note, never for the ranked animation list)

## Format mix check (mandatory before scoring)

1. Assign every candidate one format: `animation`, `explainer`, `physical gag`, `family/animal`, `gaming`, `music/dance`, or `AI-human-like`. Judge the pixels, not the label: a photorealistic human is `AI-human-like` even if a tracker or AI trend card calls it "animation".
2. `Cartoon-ready`: at least **6 of 10** ranked topics must be `animation`, `explainer`, or a `physical gag`/`family/animal` story that works with original cartoon characters; `AI-human-like` count must be **0** unless the joke survives as an original cartoon gag (then still cap at 1).
3. `All videos`: at most **2 of 10** may be `AI-human-like`, each with an explicit original-cartoon angle; still include at least **3** `animation`/`explainer` topics.
4. If the check fails, widen the animation/explainer queries (new platform, new format wording, broader date range) and re-run research. Never backfill the list with realistic AI clips just because they have high views. Record the final mix in the report and list excluded AI-human clips under "Dropped for rights/safety/AI-human-likeness".

## Research scope (asked at intake)

| Scope | Keep | Drop |
|---|---|---|
| `Cartoon-ready` (default) | Physical gags, family/animal/machine stories, clean reversals, anything original 2D characters or a code-driven `lemo-opuscar` style can tell in 20–30 s | Patterns that need real people, game/film IP, licensed sound, or a live-action setting to make sense |
| `All videos` | Every strong Shorts pattern, including gaming, real-person and IP-driven ones | Nothing on scope grounds; still drop for rights/safety at script time |

In both scopes the final characters are original. Replying `cartoon` or `all` after a report re-runs Stage 1 with the other filter and saves a new dated report; do not overwrite the old one.

## Source handling

- **Public trackers / aggregators** (weekly Shorts charts, hashtag counters, trend newsletters): useful for numbers and video IDs. They are snapshots, not YouTube's own analytics. Label them as third-party and include the collection date.
- **AI-written trend cards**: label them "AI summary of public video data". Treat their pattern descriptions as hints, not facts.
- **Direct `youtube.com` fetch**: a text fetcher sees only the page footer. Do not use it for counts.
- **Direct video links are mandatory**: every evidence set includes at least one `https://www.youtube.com/shorts/<ID>` URL. Fetch the tracker's HTML and extract the ID (e.g. `youtube.com/shorts/<ID>`, a `videoId` field, or an `i.ytimg.com/vi/<ID>/` thumbnail), then build the URL. If only an ID is available, state that the link was derived from the named tracker's dated snapshot. Never invent an ID, and never give a tracker page as the video link.
- **Facebook direct URLs**: almost always login-walled. Use public roundups; if none are found, say "no public Facebook data found for <date>" and keep the YouTube signal. Do not pretend to have scraped Facebook.
- **News articles and press releases**: good for verifying that a thing happened; check the date and avoid sponsored "trend" content.
- Require one concrete number (views, views/day, growth %) or two independent mentions of the same pattern before a topic enters the list.

## Scoring (0–10)

| Factor | Weight | What a high score looks like |
|---|---|---|
| Momentum | 40 % | Recent videos with high views/day or fast growth, not just lifetime views |
| Adaptability | 30 % | One visual gag or reversal that works with original cartoon characters in 20–30 s |
| Safety / originality | 20 % | No real person, brand, licensed sound, politics, or graphic content needed |
| Cross-platform presence | 10 % | Same pattern appears on Shorts and Reels/TikTok |

Score = round(0.4·momentum + 0.3·adaptability + 0.2·safety + 0.1·cross-platform). Sort descending. Break ties with momentum. Note explicitly if a high-view topic was dropped for rights or safety reasons.

## Turning videos into topics

- Name the *pattern*, not the uploader: "grandparent teaches a trade", "two versions of the same day", "countdown of five moments", "pet reacts to a machine", "before-a-big-release jokes".
- Keep 2–3 **direct `youtube.com/shorts/<ID>` links** as evidence, each labelled with source and snapshot date, but the script must be a new story.
- If the pattern's joke depends on a famous person, rewrite it as an original character in a similar situation. If it cannot be made original, drop it.
- Mix the final ten: animals, family, food, machines, games, strange skills, everyday mysteries, seasonal moments. No ten cat videos.

## Report rules

One reply, exactly ten numbered topics, no commentary before the list other than one line of method/date/**scope** stating that animation/explainer sources were searched and AI-human-like clips were filtered. Each entry: title (5–8 words), hook line, evidence (number + source + date), **YouTube links (one or more direct `youtube.com/shorts/<ID>` URLs, source/date labelled)**, `Format:`, `Platforms:`, why it travels, original angle, engine + style family, score. Then "My pick: #N" and the ask: "Reply with a number, 'more', 'cartoon', or 'all'." Save the same list with `templates/trend-report.md`, including its format-mix line and dropped-AI-human note.
