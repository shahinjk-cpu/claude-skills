---
name: placeforge-landmark
description: Rebuild any real place or landmark in 3D from reference photos, a map pin and a radius - a photoreal Blender (Cycles) scene on real OpenStreetMap data (streets, footprints, water, coast, railways, parks, trees), with the landmark modelled from the photos, improved by a recursive render-compare-fix loop until it matches the photo. Outputs stills, a film of any length (day, sunset, night, moving traffic and people) and an interactive Three.js page (Blender to Three.js). Renders on the user's own GPU or CPU, on a rented Vast.ai GPU, or on any SSH machine, with keys in a .env file. Use when the user asks to recreate, rebuild or model a real place, landmark, building, tower, monument, neighbourhood or city view in 3D or Blender, wants a render "like this photo", a 3D map or digital twin of a location, a flythrough or drone-style film of a place, a web 3D viewer of a place, or wants to render Blender on a rented GPU. Worked example - the Lotus Tower, Colombo.
---

# placeforge-landmark

Photos + a map pin + a radius in; a 3D place out. Three things are produced from one scene description:

1. **Stills** in Blender Cycles, matched to a reference photo.
2. **A film**, any length, with day, sunset and night, traffic, people and trains moving.
3. **An interactive Three.js page** (one HTML file) made from the same scene.

Everything runs through one command, `bin/pf` (this folder). Run `python3 <skill>/bin/pf` with no arguments for the
list. In this document `pf` means that command and `P` means the project folder.

What is generated and what is not:

| Part | Where it comes from |
|---|---|
| Streets, building footprints and heights, water, coast, railways, parks, mapped trees | OpenStreetMap inside the radius, as mapped (`pf map`) |
| Unmapped streets, and the land out to the horizon | The generator, by the region's rules in `place.json` |
| The landmark itself | **You model it** in `P/landmark.py` from the photos. This is the craft; the loop is how it gets good |
| Cars, vans, buses, people, trains, a helicopter | Downloaded CC0 models (`pf assets`). Never hand-built boxes: no model, no object. In the film and in the Three.js page they move the same way |

## Rules

1. **Ask before spending money.** Renting a GPU costs money by the hour. Rent only when the user has chosen
   `PF_COMPUTE=vast` and said go. Say the GPU and the hourly price when renting. Never rent above `VAST_MAX_PRICE`.
2. **Destroy what you rent.** When the last file is pulled: `pf gpu P down`, then `pf gpu P status` and show that
   no machine of this project is left. Never touch a machine this project did not rent.
3. **Keys stay in `.env`.** Never print, copy, commit or send an API key. `.env` is in `.gitignore`.
4. **Follow the user's standing preference for where renders run.** Some users never want renders on their own
   machine. `pf build` (no rendering) is fine anywhere.
5. **Real before invented.** Use the map before generating, a downloaded model before modelling, a measured number
   before a guessed one. Look up what the local thing really looks like (buses, trains, roofs, street lamps).
6. **Say what is true.** Map data is (c) OpenStreetMap contributors (ODbL): credit it wherever a result is shown.
   Record every downloaded asset's licence in `P/assets/assets.json`; credit CC-BY authors. Do not publish other
   people's photos; they are references only. Photos the skill found under a stated licence (`refs/cc_*`) may be
   shown with the credit in `refs/CREDITS.md`; photos from a web image search (`refs/web_*`) never.
7. **Never claim a match you did not check.** Every "it matches" comes with a `pf compare` number and the
   side-by-side you looked at.

## 0. Intake: what to ask the user

Ask only for what is missing. Use one round of questions.

- **Photos** of the place: a folder. One of them is the **target** (the view the still must match): wide, sharp,
  level horizon. Close-ups of the landmark matter more than extra wide shots. Minimum: 1 wide + 2 close-ups.
  If they have none, or too few, the skill can look for them (see "No photos" below): say so and ask if they
  also allow a web image search.
- **Where it is**: a name, a Google Maps or OpenStreetMap link, or `lat,lon`. Check with `pf locate`.
- **Radius** in metres of full detail round the pin. Guide: 300 to 500 for a building and its streets, 800 to
  1,000 for a landmark in its district (default 800), 1,500+ only if the photo's foreground needs it.
- **Outputs**: still, interactive page, film. For a film: how many seconds, 16:9 or 9:16, which times of day,
  music or not.
- **Where to render**: this machine (GPU or CPU), a rented Vast.ai GPU (they add `VAST_API_KEY` to `P/.env`), or
  an SSH machine they already have. `pf doctor` reports what this machine can do. A film on a CPU takes hours to
  days; say so and recommend renting for films.

## 1. Set up

```bash
pf doctor                                   # Blender, GPU, ffmpeg, Chrome
pf locate "Lotus Tower Colombo"             # lat, lon (and the height, if the map knows it)
pf init P --name "Lotus Tower" --lat 6.92703 --lon 79.85828 --radius 900 --height 351.5 \
        --photos <their folder> --target <the wide photo>
```

`pf init` makes `P/place.json` (the whole scene description), `P/.env` (compute and keys), `P/landmark.py` (a
template), `P/refs/`, `P/assets/assets.json`, `P/renders/LOOPS.md`. Tell the user to open `P/.env` if they chose
Vast or SSH. Every key of `place.json`: [references/config.md](references/config.md).

### No photos, or too few

```bash
pf photos P --query "Lotus Tower Colombo"      # licensed sources: Wikimedia Commons, Wikidata, Openverse -> refs/cc_*.jpg
pf photos P --browser                          # only if the user agreed: + a public image-search page -> refs/web_*.jpg
pf refs P                                      # contact sheet: look at every photo
pf photos P --drop cc_04,web_12                # set aside what is not the place (paintings, interiors, other subjects)
```

- **Tier 1** is always allowed. Each photo's licence and author go to `refs/_sources.json` and `refs/CREDITS.md`;
  these may be shown with that credit. Wikidata facts (height, year) land in `refs/_facts.json`.
- **Tier 2** needs the user's yes (`--browser`, or `PF_PHOTO_BROWSER=1` in `P/.env`). It reads a public image-search
  results page in CloakBrowser, which the command installs on first use (about 550 MB in all, outside the project;
  pinned to 0.6.3, the version whose free build needs no licence key; tell the user before the first run). If it
  cannot install or start, the Chrome on their machine is used instead, with a fresh empty profile. Its rules are fixed: read-only, public
  pages, no login, one page at a time, 10 s between searches, three searches and 30 images at most, and on a
  verification wall or an empty page it stops: no retry, no other engine. Never work round a block.
- `web_*` photos have **no known licence**. They are references only: never put them in a film, a page, a
  thumbnail, a repository or any message that leaves the machine. They are git-ignored.
- Search results are noisy. Look at the contact sheet, drop what is not the place, then choose the target yourself
  (wide, level, daylight) and write it to `place.json` `refs.target`. Tell the user what was found, from where, and
  which photo you chose.
- Still short of one wide view and two close-ups: ask the user. Do not model a landmark from one photo.

## 2. Dig, then look

- Facts first: total height, heights of the parts, materials, year (Wikipedia, Structurae, Skyscraper Center, the
  architect). Put the height in `place.json` `landmark.height_m`.
- `pf refs P` writes `refs/_contact.jpg` (all photos) and `refs/_target_grid.jpg` (the target with a 50 px grid).
  Read both at full size. Then crop and zoom the close-ups: they fix shapes the wide shot cannot.
- Note the region: which side traffic drives on, roof types and colours, wall colours, tree kinds, water colour,
  rooftop water tanks or not. These go in `place.json` `region` (colours are linear RGB, 0 to 1).

## 3. The map

```bash
pf map P            # -> P/map/osm.json and P/map/preview.png
```

Read `map/preview.png`: the pin must sit on the landmark, the red ring is the radius. Overpass is tried first and
is often down; the OpenStreetMap API is the fallback (complete inside the radius, no far ring). `pf map P --reuse`
later adds the far ring (coast, big water, land use out to `far_radius_m`) when Overpass answers. If the report
says only a few buildings are mapped, the generator fills the streets; raise `infill.density`.

## 4. Match the camera to the target photo

Read four numbers off `refs/_target_grid.jpg`: the horizon row, the row where the landmark meets the ground, the
row of its top, and its column. Then:

```bash
pf camera P --horizon 482 --base-row 647 --top-row 92 --col 790 --height 351.5 --focal-mm 28 --bearing 355
```

- It solves the camera's distance and height (a level camera with lens shift, like most architecture photos).
- `--bearing` is the compass direction the photo looks. Find it on `map/preview.png` from what is left and right
  of the landmark in the photo. Or give `--feature X,Y,COL`: one map feature (metres east, north of the pin) and
  the photo column where it appears; the bearing is solved.
- No EXIF focal length: start at 28 mm for a wide view and let the first blend tell you (surroundings too spread
  out = lens too short).
- Then look at `map/preview.png` again: the blue wedge is the camera's view. It must contain what the photo shows.

No target photo, or only close-ups: skip this; the views `hero`, `wide`, `close`, `top`, `street` exist anyway.

## 5. Model the landmark

Write `P/landmark.py`: `build(mp)` makes the landmark at the origin and returns `{"height": metres}`; `KEEP_OUT`
lists the discs the generator must leave empty. How to measure, the helpers, materials, night lighting and what
travels to the web viewer: [references/landmark.md](references/landmark.md). A complete example:
[examples/lotus-tower/landmark.py](examples/lotus-tower/landmark.py).

Check the scripts before every render, on any machine, for free:

```bash
pf build P                  # ends with "pf: BUILD OK"
pf web P && pf shot P hero  # a quick look in the Three.js viewer: shapes, placement, the map. Not the final look
```

## 6. The recursive perfection loop

This is the heart of the skill. One loop:

```bash
pf assets P                                   # once: CC0 vehicles, people, helicopter, ground textures (--remote on a rented machine)
pf render P --name loop01 --view photo,close  # previews (half size, 64 samples)
pf compare P loop01_photo                     # numbers + _sbs.jpg, _blend.jpg, _diff.jpg
pf log P loop01 "what changed" "the worst gap now"
```

1. Read the table and **look** at `_sbs.jpg` (side by side) and `_blend.jpg` (50% overlay).
2. Rank the gaps in this order and fix only the top one to three:
   geometry and placement (doubled edges in the blend; `edge match` low) > exposure and sky > materials and
   colours > detail density > small props.
3. Fix by argument first, code second. Any `place.json` key can be overridden for one run:
   `pf render P --name loop02 look.exposure.day=0.6 look.haze.day=0.00003 region.pitched_share=0.1`.
   When a value wins, write it into `place.json`.
4. Render again. Stop when the diff stops falling and nothing in the side-by-side reads as fake. Then
   `pf render P --name final --final`.

The loop is recursive in three ways:

- **Down the scales.** Converge the wide view first, then descend: district (`view=wide`, an 85 mm crop), the
  landmark (`view=close`), the street (`view=street`, eye level), a single detail. Each level has its own
  cameras in `place.json` `views` and its own loop. A gap found close up sends you back into the model, and the
  wide view is rendered again afterwards. Users judge at street level as well as from the air.
- **Across outputs.** Each film shot and each viewer view is checked the same way (`pf film render P pick=...`,
  `pf shot`), and fixes go back to the one scene description.
- **Across projects.** When a project ends, add what made it real, in two or three lines, to
  [references/lessons.md](references/lessons.md). Read that file before starting the next place. The skill gets
  better each time it is used.

What to tune and what each knob does: [references/look.md](references/look.md).

## 7. Film

Ask: seconds, aspect, times of day, music. Then:

```bash
pf film plan P --seconds 30 --tod day,sunset,night   # -> P/film/shots.json: edit the shots
pf build P anim=1                                     # checks every shot and the per-frame update
pf film render P pick=1,150,400                       # stills of chosen frames: look before paying for all of them
pf film render P                                      # all frames (on a rented GPU: runs in the background)
pf film encode P --music track.mp3 --music-start 12   # -> P/film/<name>_film.mp4, fades in and out
```

Shots are `orbit`, `dolly`, `topdown` or `photo` moves in metres and compass bearings (`engine/pf_cam.py` has the
fields). One Blender process renders one time of day; frames can render in any order on several machines because
every mover's position is a function of time. Portrait: `film.w` 1080, `film.h` 1920 in `place.json`. Music needs
a licence the user holds; put the credit line in the video description.

## 8. Interactive page (Blender to Three.js)

```bash
pf web P                      # -> P/web/index.html, one self-contained file
pf shot P photo --t 40        # headless Chrome screenshot (view name, sun elevation); also prints the frame rate
```

The page shows the same city and landmark with orbit controls, view buttons and a time-of-day slider, and the same
life as the film: traffic keeping to its side of the road, parked cars, people walking, trains, the helicopter
circling with both rotors turning, head lamps at night. It is a real-time look, not Cycles. Shader detail made
with nodes does not travel: give such materials an average colour with `pf.viewer_color(...)` (see the landmark
reference). Vehicle models are thinned to about 1,100 triangles for the page; people are kept whole (a thinned
figure falls apart).

## 9. Where renders run

`P/.env` decides: `PF_COMPUTE=local | vast | ssh`. `pf render` and `pf film render` do the same thing on all three.

```bash
pf gpu P offers          # vast: what is on offer under VAST_MAX_PRICE
pf gpu P up              # vast: rent + install Blender (about 3 minutes). ssh: install Blender there
pf assets P --remote     # the machine downloads the models itself
pf render P ...          # scripts go up, previews come down
pf gpu P down            # vast: destroy. Then: pf gpu P status
```

Traps and their fixes (slow hosts, OptiX failures, killed jobs, transfers): [references/compute.md](references/compute.md).

## Limits to state plainly

- Ground is flat. Hilly sites need terrain; not built yet.
- Flyovers and tunnels are drawn at grade; only bridges over water get a deck.
- The far ring is generated, not mapped building by building.
- A camera with a tilted horizon or strong lens distortion will not match exactly.
- Traffic follows lanes at one speed per lane: no junction rules, no overtaking. People walk; they do not stand, sit or cross.
- One helicopter on a circle (`life.helicopter`, `life.heli_radius`, `life.heli_height`, `life.heli_bearing`); no birds or aircraft (frozen wings read as fake).
- Tested with Blender 5.2 on macOS (build, export, viewer). The rented-GPU path is ported from the scripts that
  rendered the Lotus Tower; check the first preview before queuing a film.
