# Latency and responsiveness

Use with `rec_audit.py measure`. Always report a timing with its resolution (± one frame) and how the input time was found. Grade only what the recording supports. Below 50 fps, do not judge smoothness, only stalls of 2 or more frames.

## How the script measures
- **Time:** from each frame's real timestamp. Recorders write frames only when the screen changes, so a long gap means nothing changed, or the recorder dropped frames.
- **First visible change:** usually feedback (pressed state, ripple, cursor or caret). Confirm it on the strip.
- **First substantial change:** 3% or more of the screen changes in one frame, or an area of 8% or more. Usually the response. A small result (toast, label, counter) will not count: check the change list.
- **Settled:** the last change before 500 ms with no change. Looping animations, clocks and the cursor keep a screen from settling; `--ignore` them.
- **Frozen:** 250 ms or more with no change at all between the input and the response, meaning the user saw nothing.
- **Busy:** a small area that keeps changing in the same place for 400 ms or more: spinner, progress, animation, or the cursor.

## Thresholds from platform and research sources

### 1a. Cross-platform thresholds

| Interaction / metric | Good | Needs work | Poor | Source |
|---|---|---|---|---|
| Discrete input (tap, click, key) to first visible response | ≤100 ms (feels instant) | 100–250 ms (noticeable) | >250 ms (Apple tools flag a "hang") / >1 s (flow broken) | [NN-RT] [RAIL] [AP-HANG] |
| Web interaction latency (INP, p75) | ≤200 ms | 200–500 ms | >500 ms | [CWV-INP] |
| Direct manipulation (drag, scroll, pinch) | Content tracks the finger or cursor every frame | Lag of 1–2 frames is visible | Content detaches from the pointer or stalls | [NN-RT] [RAIL] |
| Animation frame budget | 60 Hz: 16.7 ms. 90 Hz: 11 ms. 120 Hz: 8.3 ms | Occasional missed frames | Sustained misses | [AND-JANK] [AP-HITCH] |
| Apple hitch rate | ≤10 ms/s | 10–25 ms/s (warning) | 25–50 ms/s critical; >50 ms/s needs immediate attention | [AP-HITCH] |
| Android frame class | <16 ms | Slow frame: 16–700 ms | Frozen frame: 700 ms–5 s. ANR: >5 s with no input response | [AND-JANK] |
| Web page main content visible (LCP, p75) | ≤2.5 s | 2.5–4.0 s | >4.0 s | [CWV-LCP] |
| Web layout stability (CLS, p75) | ≤0.1 | 0.1–0.25 | >0.25 | [CWV-CLS] |
| Web load to interactive (RAIL) | Repeat load ≤2 s | First load ≤5 s on mid-range mobile, slow 3G | >5 s | [RAIL] |
| Android cold start (time to first frame, TTID) | well under 5 s | — | ≥5 s is "excessive" | [AND-LAUNCH] |
| Android warm / hot start | <2 s / <1.5 s | — | ≥2 s / ≥1.5 s is excessive | [AND-LAUNCH] |
| iOS launch | First frame "instantly"; people won't wait more than "a couple of seconds" | — | Watchdog kills a launch that takes too long | [AP-LAUNCH] [AP-LAUNCHDOC] |
| Attention limit for any wait | <1 s keeps flow | 1–10 s needs a busy indicator | >10 s needs percent-done, a time estimate and Cancel | [NN-RT] [NN-PROG] |

### 1b. Loading-indicator rules

| Expected wait | Correct feedback | Wrong | Source |
|---|---|---|---|
| <1 s | None beyond the result. A spinner that flashes for a frame or two counts as a defect | Spinner or skeleton that flickers briefly | [NN-PROG] [NN-SKEL] |
| ~1–2 s | Some busy signal: pressed state, busy cursor, or inline indicator | Nothing changes, so the user taps again | [NN-RT] [NN-PROG] |
| 2–10 s | Looping spinner (for a single module) or skeleton (for a full page), ideally with specific text such as "Loading comments…" | Static "Loading…" text. A frame-only skeleton showing just header and footer | [NN-PROG] [NN-SKEL] [AP-PROG] |
| >10 s | Determinate progress bar, time estimate, Cancel option | Indeterminate spinner beyond 10 s | [NN-PROG] [NN-SKEL] |
| Any | Keep the indicator moving. A frozen spinner reads as a crashed app | Stalled bar | [AP-PROG] |
| Any | Switch indeterminate to determinate once the total is known. Never morph a spinner into a bar | Spinner changing into a bar | [AP-PROG] |
| Any | Progress advances at an even pace (no 90 % in 5 s, then a long stall) | Jumpy or backward progress | [AP-PROG] |
| macOS | Spinner for background work, without a label | — | [AP-PROG] |
| iOS launch | Launch screen nearly identical to the first screen, with no text and no branding | Splash or ad, then a visible flash on swap | [AP-LAUNCH] |

### 1c. What can be measured from a 30/60 fps recording

| Measurement | How to read it from frames | Resolution and caveats |
|---|---|---|
| Frame period | 30 fps = 33.3 ms per frame. 60 fps = 16.7 ms per frame | Any latency is ±1 frame. A 30 fps capture cannot judge 60 Hz smoothness, only stalls of 2 or more frames (≥67 ms) |
| Input moment (t0) | Android "Show taps" dot, iOS AssistiveTouch or touch-indicator overlay, cursor-click halo, key-press overlay, or the first frame of a pressed state | Without a visible input marker, report latency as "from first visible press state" |
| Input to first visual response | Frames from t0 to the first changed pixel in the target region (highlight, ripple, cursor change) | Compare with 100 ms (6 frames at 60 fps, 3 at 30 fps) and 250 ms (15 / 7.5 frames) |
| Time to settled | t0 to the last frame where the region changes (content loaded, animation finished, no further shifts) | Compare with 1 s / 10 s and the LCP-like 2.5 s |
| Spinner / skeleton duration | First to last frame the indicator is visible | <1 s with a spinner flags flicker. >10 s with an indeterminate indicator flags missing progress |
| Stutter / hitch | Runs of identical consecutive frames (a frame-diff of ~0) during motion that should be continuous: scroll, transition, drag | At 60 fps capture, 1 repeated frame ≈ 1 missed vsync. ≥42 identical frames (~700 ms) ≈ Android "frozen frame". Rule out recorder drops: if the clock or cursor keeps moving while content is static, the app hitched |
| Hitch ratio estimate | Sum of the extra time from repeated frames ÷ animation duration (ms/s) | Compare with Apple's 10 / 25 / 50 ms/s bands |
| Layout shift | Visible content jumps position without the user causing it, especially more than 500 ms after the last input | CLS can't be computed exactly. Estimate as shifted area fraction × distance fraction of the viewport. Flag any jump of a text block or button the user was about to hit |
| Animation duration | Frames from motion start to motion end | Compare with M3 tokens (50–1000 ms; most UI 200–500 ms) or Windows (83 / 167 / 250 / 333 ms). >500 ms for frequent UI is sluggish |
| Flashing | Count luminance flips per second | >3 flashes in any 1 s fails WCAG 2.3.1 |
| White flash on open | Blank white or black frame(s) before the first content frame (window open, route change, dark-mode app) | Electron: suggests missing `backgroundColor` or `ready-to-show`. iOS: launch screen doesn't match the first screen |

## Severity mapping for timing findings
### Latency thresholds to cite (sources: Nielsen response-time limits 0.1/1/10s; Google RAIL; Core Web Vitals; and the skills above)
| Moment | Good | Needs work | Poor / finding |
|---|---|---|---|
| Tap/click to first visual feedback (pressed state, ripple) | ≤100ms | 100–200ms | >200ms (P2); >1s with no change (P1) |
| Action to result (mutation, toggle, navigation) | ≤500ms (Vercel's mutation target) | 0.5–1s | >1s without an indicator (P1); >1s with an indicator (P2) |
| Screen or view load to usable content | ≤1s | 1–3s with skeleton or progress | >3s (P1); >10s (P0 unless there is progress and a way to cancel) |
| Loading indicator appearance | none for <~300ms work (avoid flashes) | | spinner flashes for 1–3 frames (P3), or no indicator at all past 1s (P1) |
| Animation duration (UI) | 100–300ms (modals and drawers up to 500ms) | 300–500ms on small UI | >500ms on frequent UI (P2); any animation on 100+/day actions |
| Toast / transient message | 3–5s visible | | under 2s for text that needs reading; errors that auto-dismiss |
| Scroll/animation smoothness | steady frame cadence at the recording fps | occasional dropped frame | visible stutter: repeated or held frames (more than 2 consecutive identical frames during motion) (P2) |
| Layout shift after first paint | none | small, input-triggered | content jumps under the finger or cursor without input (P1 if it causes a mis-tap) |

Always state timing precision (±1 frame), and say when input time is inferred.
