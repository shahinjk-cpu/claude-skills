# place.json: every key

One file describes the place. Anything missing takes the default in `engine/pf_core.py` (`DEFAULTS`). Any key can be
overridden for one run with a dotted argument: `pf render P look.exposure.day=0.6`. Colours are linear RGB, 0 to 1.
Positions are metres east, north, up from the pin. Bearings are compass degrees (0 north, 90 east).

| Key | Meaning |
|---|---|
| `name`, `lat`, `lon` | The place and its pin (the landmark's centre) |
| `radius_m` | Full-detail radius: mapped streets, footprints, trees |
| `far_radius_m` | How far the generated city reaches (`"auto"` = 4 x radius, 3 to 8 km) |
| `landmark.height_m` | Total height; frames the automatic views and film shots |
| `landmark.clear_radius_m` | Clear mapped footprints and trees within this distance of the pin (or use `KEEP_OUT` in `landmark.py`) |
| `landmark.remove_names` | Names of mapped buildings to drop (the map's stand-in for the landmark) |
| `refs.target` | The photo the still must match |
| `camera` | Written by `pf camera`: `focal_px`, `horizon_row`, `height_m`, `distance_m`, `bearing_deg`, `offset_right_m`, `ref_w`, `ref_h` |
| `views` | Extra cameras: `{"name": {"from": [x, y, z], "to": [x, y, z], "lens": 35}}` |
| `compare.regions` | Named boxes on the target in its own pixels `[x0, y0, x1, y1]`: sky, water, the landmark's parts. With them `pf compare` scores those; without, a 6 x 4 grid |
| `time.tod` | `day`, `sunset` or `night` (or `tod=night` per run) |
| `time.<tod>.sun_elevation`, `.sun_bearing` | Where the sun (moon at night) is. `pf sun P --when ... --tz ... --write day` computes it |
| `look.exposure` | Per time of day, in stops |
| `look.agx` | `base`, `mh`, `punchy`, `none` (processed tourist photos: punchy) |
| `look.saturation`, `look.contrast` | Compositor finish |
| `look.sky` | `physical`, or `gradient` with `look.sky_stops` `[[height 0..1, [r, g, b]], ...]` matched to the photo |
| `look.sky_camera`, `look.sky_light` | Sky brightness as seen, and as a light source (split to kill a cyan cast) |
| `look.sun_strength` | Per time of day |
| `look.haze` | Scatter density per metre, per time of day (0 = none). `look.haze_top_m`: thickness of the haze layer |
| `look.clouds` | 0 to 1 cover of volumetric clouds. `look.cloud_shadows`: false when the photo is in full sun |
| `region.drive` | `left` or `right` |
| `region.floor_m`, `region.default_floors` | Storey height; floors of buildings the map gives no height for |
| `region.walls`, `region.roofs_flat`, `region.roofs_pitched` | Weighted palettes `[[[r, g, b], weight], ...]` |
| `region.pitched_share` | Share of small buildings with pitched roofs. `region.glass_share`: tall buildings as curtain wall |
| `region.roof_tanks` | 0 to 1: rooftop water tanks (South Asia, Mediterranean, Latin America) |
| `region.weathering` | 0 clean, 1 monsoon streaks and patchy roofs |
| `region.trees` | Mix of `broad`, `round`, `tall`, `palm`, `conifer`. `region.tree_density`: multiplier |
| `region.water`, `region.sea` | Body colours. `region.shore`: `soft` or `wall`. `region.wind_bearing` |
| `infill.density` | `"auto"`, 0 (off) to 1: lots along streets the map shows without buildings |
| `infill.lot_m`, `infill.floors` | Lot size range and floors of generated buildings |
| `far.urban`, `far.trees` | Density of the generated far ring |
| `life.vehicles`, `life.people` | 0 to 1. `life.street_lamps`: true or false |
| `life.helicopter` | 1 or 0. `life.heli_radius`, `life.heli_height` in metres (0 = from the landmark's height), `life.heli_bearing`: where on its circle it is at time 0 |
| `web.links` | Links shown in the Three.js page's panel: `{"Read the article": "https://...", "GitHub": "https://..."}` |
| `render.w`, `render.h`, `render.samples`, `render.preview_pct`, `render.preview_samples` | Stills |
| `film.fps`, `film.w`, `film.h`, `film.samples` | Films |
