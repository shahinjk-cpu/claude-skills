# UI, design and motion checklist

Run against settled full-resolution frames (F), frame sequences and strips (M). Items marked N cannot be judged from video: list them under Not assessable. Use the check IDs in findings. Judge against the product's own conventions and its platform (see platforms.md).

[F] = still frame · [M] = motion/timing across frames · [N] = not assessable from video (record under Not assessable)

**1. Layout & alignment**
- [F] LAYOUT-OVERFLOW: content cut off at the screen edge, horizontal scroll on mobile, desktop layout squeezed into a phone
- [F] LAYOUT-OVERLAP: elements overlapping (text on text, a button over content, a FAB covering the last list item)
- [F] LAYOUT-CLIP: text or icons clipped by their container (descenders, badges, truncated buttons)
- [F] ALIGN-NEARMISS: sibling edges or baselines visibly a few px off a shared line (estimated); icon not centred or not on the text baseline
- [F] ALIGN-GRID: sections don't share a content margin or gutter; each block starts at a different left edge
- [F] SAFE-AREA: content or tap targets under the notch, status bar, Dynamic Island or home indicator; content hidden behind a fixed header, footer or tab bar
- [F] RESPONSIVE: broken breakpoint layout, orphaned single items on a row, unbalanced columns
- [F] IMAGE-QUALITY: stretched, pixelated, upscaled, wrong aspect ratio or badly cropped images; a broken-image icon
- [M] LAYOUT-SHIFT: content jumps after first paint or when async content arrives, without input; a skeleton that doesn't match the final layout
- [M] PRESS-SHIFT: pressed or hover state changes layout bounds (neighbours move)

**2. Spacing**
- [F] SPACING-INCONSISTENT: same-role gaps differ (card padding, list row height, section spacing)
- [F] SPACING-CRAMPED: elements jammed edge-to-edge; touch targets crowded with no gap (under about 8px)
- [F] SPACING-PROXIMITY: a label closer to the wrong field; related items separated; unrelated items grouped (Gestalt)
- [F] SPACING-RHYTHM: no vertical hierarchy of spacing (every gap is equal, so sections don't separate)
- [F] SPACING-WASTE: large accidental voids, or an unbalanced empty area

**3. Typography**
- [F] TYPE-HIERARCHY: heading, body and meta tiers can't be told apart, or tiers rely on size alone
- [F] TYPE-SPRAWL: too many sizes, weights or families; same-role text in different sizes across screens
- [F] TYPE-LEGIBILITY: body text visibly tiny (below about 16px mobile, 12px anywhere, estimated); thin weight on a busy background; over-tight tracking
- [F] TYPE-MEASURE: lines too long (more than about 75 characters on desktop) or too short; edge-to-edge paragraphs on a tablet
- [F] TYPE-TRUNCATION: important labels truncated with no way to see the full text; ellipsis in the middle of key info; awkward widows or orphans in headings
- [F] TYPE-DETAILS: `...` vs `…`, straight quotes, inconsistent capitalisation (Title vs sentence case), numbers that should be tabular jittering in width ([M] when they update)
- [N] Dynamic Type or text-scaling support (unless the recording shows a large-text setting)

**4. Colour & contrast**
- [F] CONTRAST-TEXT: text likely below 4.5:1 (3:1 for large text). Estimated; verify with a checker
- [F] CONTRAST-UI: control borders, icons, focus or selection indicators, and placeholder text likely below 3:1
- [F] COLOR-ONLY: state or meaning carried by colour alone (error, selection, status, chart series)
- [F] COLOR-SEMANTIC: status colours inconsistent (two reds, success and info swapped); the primary colour overused so nothing stands out
- [F] TEXT-ON-IMAGE: text over a busy image or gradient with no scrim
- [F] DARK-MODE: inverted rather than designed dark mode; dividers or borders disappearing; low-contrast muted text; a weak scrim
- [F] CHEAP-TELLS: muddy gradients, harsh drop shadows, clashing colours, default-blue links, random shadow or elevation values

**5. Visual hierarchy**
- [F] HIERARCHY-FLAT: no focal point; everything has equal weight; fails the squint test
- [F] CTA-AMBIGUITY: no clear primary action, or several equal-weight CTAs; the secondary action visually louder than the primary
- [F] OVERLOAD: too many options at a decision point (more than about 4–7, ungrouped), walls of text, no progressive disclosure
- [F] CONTENT-PRIORITY: the core content is below secondary content or the fold on mobile; the key info isn't front-loaded

**6. Consistency**
- [F] PATTERN-DRIFT: the same component role looks different across screens (button style, card, header, radius, shadow); record estimated values per screen
- [F] ICON-INCONSISTENT: mixed icon families, stroke weights, or filled vs outline at the same level; emoji used as structural icons
- [F] TERM-DRIFT: the same concept named differently across screens; an action renamed mid-flow
- [F] PLATFORM-CONVENTION: non-native patterns that break platform expectations (an Android back arrow on iOS, a custom control where a native one is expected)
- [M] BEHAVIOR-DRIFT: the same interaction behaves differently in different places (one sheet slides, another fades; one list swipes, another doesn't)
- [M] SURFACES-DISAGREE: after an action, two surfaces show different data (badge count vs list, header vs detail)

**7. States: loading, empty, error, disabled, success**
- [F] STATE-LOADING: blank screen while loading; a spinner where a skeleton belongs; a loading button that loses its label
- [M] STATE-LOADING-TIMING: indicator flashes for a few frames; no indicator for a wait over 1s; spinner never resolves (stuck)
- [F] STATE-EMPTY: an empty state with no explanation or next action; a blank chart or axis frame (only if the recording reaches it)
- [F] STATE-ERROR: raw or technical error text, an error with no cause or remedy, a global banner only (not by the field), input lost after an error
- [F] STATE-DISABLED: disabled looks the same as enabled (or vice versa); read-only indistinguishable from disabled; a disabled submit with no reason shown
- [F] STATE-SUCCESS: no confirmation after a completed action (only judged if the action visibly completed)
- [M] STATE-STALE: old or wrong content shown briefly before the correct content (wrong brand, previous user's data, placeholder text); half-rendered states; raw Markdown or template tokens flashing
- [F] PLACEHOLDER-LEAK: lorem ipsum, "undefined", "null", "NaN", `{{var}}`, test data, debug overlays visible
- [N] Hover states on touch-only recordings; states not exercised in the recording (coverage note only)

**8. Feedback & affordance**
- [M] NO-FEEDBACK: a tap or click gives no pressed state or response (see the latency table)
- [M] DOUBLE-ACTION-RISK: the user repeats a tap because nothing happened; a duplicate result appears
- [F] FAKE-AFFORDANCE: looks interactive but isn't (observed tap with no effect [M]); interactive but doesn't look it (plain text links, flat buttons)
- [F] TOUCH-TARGET: targets visibly smaller than about 44pt/48dp (24px web floor), estimated from known reference sizes such as the screen width
- [M] MISTAP: the recording shows a missed or wrong target hit (tap lands next to the control, or the wrong item opens)
- [M] GESTURE-FEEDBACK: drag, swipe or pull doesn't track the finger; no rubber-band or threshold feedback
- [F] SWIPE-HIDDEN: critical actions available only through an undiscoverable gesture (judge when the recording shows the gesture revealing them)
- [M] TOAST-TIMING: a toast disappears too fast to read; errors auto-dismiss; a toast covers primary controls
- [M] TOOLTIP-TIMING: a long delay on each tooltip, or no delay on the first

**9. Navigation & flow**
- [F] NAV-LOCATION: the current location isn't indicated (no active tab or nav state, no title)
- [F] DEAD-END: a screen with no forward action or way out (including error and empty states)
- [F] PROGRESS-BLIND: a multi-step flow with no step indicator
- [F] MODAL-ESCAPE: a modal or sheet with no visible close or cancel
- [F] NAV-OVERLOAD: bottom nav with more than 5 items, icon-only nav without labels, mixed nav patterns at one level
- [M] BACK-BROKEN: back loses scroll position, filters or input; an unexpected jump to home; the back stack reset
- [M] TRANSITION-DIRECTION: forward and back transitions animate inconsistently or in the wrong direction; a modal not animating from its trigger
- [M] FLOW-FRICTION: unnecessary steps or screens between intent and result (count the taps for the core job); a redundant confirmation
- [M] RECALL-TAX: the user must remember information from an earlier screen (shown navigating back to check something)
- [F] DESTRUCTIVE-UNGUARDED: a destructive action placed next to normal actions with no visual separation ([M] no confirmation or undo seen when it is used)
- [F] TRUST-GAP: money or personal-data moments with no reassurance
- [F] DARK-PATTERN: confirmshaming, pre-ticked consent, fake urgency, hidden cancel

**10. Forms & input**
- [F] FORM-LABEL: placeholder-only labels (verify across frames that the label disappears on typing [M]); missing required markers
- [F] FORM-LAYOUT: multi-column forms (except short related fields); ambiguous label proximity
- [M] FORM-VALIDATION: premature validation while typing; errors only on submit, at the top; errors that don't clear once fixed; input wiped after an error
- [M] KEYBOARD-OBSCURES: the on-screen keyboard covers the focused field or the submit button; no scroll-into-view
- [F] KEYBOARD-TYPE: wrong keyboard for the field (text keyboard for email, phone or number), visible in the recording
- [M] INPUT-ZOOM: iOS auto-zooms on focus (input text under 16px)
- [M] INPUT-LAG: typed characters appear late (judge from frames vs the keyboard key highlight)
- [N] autocomplete or autofill attributes, paste blocking (unless attempted on camera), password-manager compatibility

**11. Motion & animation**
- [M] MOTION-DURATION: UI transitions visibly too slow (more than about 300ms for small UI, 500ms for modals) or too abrupt (instant snaps where continuity is needed); measure in frames
- [M] MOTION-EASING: linear or ease-in feel on entrances (slow start); bounce without purpose
- [M] MOTION-ORIGIN: popovers or menus growing from the centre instead of their trigger; scale-from-zero "comes from nowhere"
- [M] MOTION-JANK: dropped, repeated or held frames during scroll or animation; stutter on list scroll; frozen UI (a long task)
- [M] MOTION-FLICKER: a flash between states, crossfade dip (brightness dip or flash at the midpoint), elements blinking or re-mounting, an entrance replaying on content that already existed
- [M] MOTION-ORPHAN: old content lingering after the transition ends; a z-order swap at the end of a transition; shadow pop at start or end
- [M] MOTION-EXCESS: too many things animating at once; decorative motion on high-frequency actions; autoplay over 5s with no pause control
- [M] MOTION-BLOCKING: input ignored until an animation finishes (a tap during the transition is lost)
- [M] MOTION-STAGGER: lists all popping at once, or a very slow stagger (more than about 80ms per item)
- [M] MOTION-ASYMMETRY: exit slower than enter; system responses slower than deliberate user phases
- [N] Reduced-motion support (unless a reduced-motion recording is provided); flashing over 3/sec can be flagged [M] if seen

**12. Content & copy**
- [F] COPY-LABEL: vague CTA labels ("OK", "Submit", "Continue") where a specific verb is needed
- [F] JARGON-LEAK: internal, system, legal or error-code language shown to users
- [F] ERROR-VAGUE: error copy without what happened and how to fix it
- [F] COPY-TONE: playful tone at error, money or data moments; blame-y or apologetic errors
- [F] COPY-QUALITY: typos, grammar, inconsistent capitalisation or punctuation, mixed languages, untranslated strings
- [F] COPY-COHERENCE: title, body and metrics that don't tell one story; numbers or dates formatted inconsistently across screens
- [F] COPY-DENSITY: walls of text, filler, redundant instructions

**13. Accessibility visible from pixels**
- [F] A11Y-CONTRAST: same as CONTRAST-TEXT and CONTRAST-UI
- [F] A11Y-COLOR-ONLY: same as COLOR-ONLY
- [F] A11Y-TARGET: same as TOUCH-TARGET
- [F] A11Y-TEXT-SIZE: very small text; disabled zoom can't be seen [N]
- [F] A11Y-ICON-LABEL: icon-only controls with no visible label where the meaning is ambiguous
- [F] A11Y-FOCUS: a visible focus ring is missing during keyboard use, judged only if the desktop or web recording shows keyboard navigation [M]; otherwise [N]
- [M] A11Y-MOTION: flashing content, parallax or large motion that could trigger vestibular issues
- [M] A11Y-TIMEOUT: content that times out or auto-advances too fast to read
- [N] Screen-reader labels and order, semantic roles, alt text, keyboard traps (unless shown), focus management, reduced-motion handling, Dynamic Type, captions (unless media is shown)

**14. Latency (the timing checks, measured per action)**
- [M] LATENCY-FEEDBACK: tap to first visual response over 100ms (P2 over 200ms; P1 over 1s)
- [M] LATENCY-ACTION: action to result over 1s without an indicator
- [M] LATENCY-VIEW: screen to usable content over 3s
- [M] LATENCY-SPINNER-FOREVER: an indicator that never resolves within the recording
- [M] LATENCY-PROGRESSIVE: content arrives in jarring pieces (pop-in, reflow) instead of skeleton-matched progressive loading
- [M] LATENCY-PERCEIVED: missing optimistic updates for safe actions; blocking modals for background work
- [M] LATENCY-STARTUP: app launch or splash to interactive (report it, with build and device caveats)
- [N] Network, server, CPU or main-thread causes: only "likely cause (inferred)" unless logs or traces are provided
