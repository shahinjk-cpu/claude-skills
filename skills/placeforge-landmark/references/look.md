# Look: what to tune, in what order

Fix in this order. Later items cannot rescue earlier ones.

## 1. Geometry and placement (`edge match` low, doubled edges in `_blend.jpg`)

- Landmark right, surroundings wrong scale: the focal length. Longer lens = surroundings larger. Rerun `pf camera`.
- Everything shifted sideways: `--col`, or the bearing. Tilted: the photo's horizon is not level (not supported).
- Landmark the wrong shape: back to `landmark.py` with the close-ups.
- The ordinary city decides realism first. From a high viewpoint a low-rise city is roofs and trees; a few percent
  too many mid-rises reads as a skyscraper forest. Set `region.default_floors`, `infill.floors`, `far.urban`.

## 2. Exposure and sky

- `look.exposure.<tod>` in stops. Compare the sky regions first.
- The physical sky can come out pale at high sun. `look.sky = "gradient"` with `look.sky_stops` sampled from the
  photo is often closer. `look.sky_light` lower than `look.sky_camera` removes a cyan cast on walls.
- `look.haze.<tod>` and `look.haze_top_m`: a haze layer that is too tall greys the low sky; 800 m keeps it blue.
- `look.clouds`: volumetric clouds beat any painted sky. Keep `look.cloud_shadows` false when the photo is in full
  sun (one cloud shadow can land exactly on the landmark).
- Sun: `pf sun P --when "<date time>" --tz <hours> --write day` if the photo's time is known; otherwise read the
  shadows (direction on the map gives the bearing, length over height gives the elevation).

## 3. Materials and colours

- `region.walls`, `region.roofs_flat`, `region.roofs_pitched`, `region.pitched_share`: sample real roofs and
  walls from the photo (convert sRGB to linear: `(v / 255) ** 2.2`).
- `region.weathering`: streaks, patchy roofs, rust on sheds. Clean cities 0.2, monsoon cities 1.0.
- `region.water`: the body colour. Reflections do most of the work; too bright a body colour looks like paint.
- Trees: `region.trees` mix and `region.tree_density`. Dark crowns read as holes: keep foliage sunlit.
- Ground textures and vehicle models make the close views: `pf assets P`.

## 4. Detail density, then small props

- `region.roof_tanks`, `life.street_lamps`, `life.vehicles`, `life.people`.
- Close views need their own grade: more sky fill and less contrast than the wide photo view
  (`look.sky_light=0.9 look.contrast=3 agx=base`).
- Night: no haze, no cloud deck (lit by thousands of lamps they turn to noise). Windows lit about a quarter.

## Reading `pf compare`

- `colour diff`: sum of absolute sRGB differences of the region means. Use `compare.regions` in `place.json`
  (sky top, sky horizon, water, the landmark's parts, near city, far city) so the number means something.
- `edge match`: correlation of the edge maps, 1 = edges coincide. Fix geometry before colour while it is low.
- Numbers find the gap; eyes decide. Open `_sbs.jpg` and `_blend.jpg` every loop.
- Log every loop: `pf log P loop07 "what changed" "worst gap now"`. A diff that rises after a change is information.
