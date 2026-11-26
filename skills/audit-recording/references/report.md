# Report format

## Severity scale (merged: Nielsen impact × serebano P-levels × impeccable)
| Level | Name | Criteria (any one is enough) |
|---|---|---|
| **P0** | Blocker | Core job impossible or dead-ended; data loss or wrong action taken; privacy leak visible on screen; crash, freeze or blank screen longer than 10s with no recovery; content unreadable on a primary path. |
| **P1** | Major | The core flow is broken, misleading or slow. Triggers: **no visible feedback within 1s of an action**; **an action takes over 1s or a view over 3s without progress indication**; two surfaces disagree (counter vs list); clear contrast failure on primary text or a CTA; clipped or overlapping primary content; a pattern that misleads (fake affordance on the main path); a repeated, systemic issue on a foundational component. |
| **P2** | Minor | Noticeable friction with a workaround: inconsistent component styling, secondary contrast issues, cramped spacing, weak hierarchy, a flicker or flash under 300ms, mild jank, slow-but-indicated loads (1–3s), vague copy. |
| **P3** | Polish | Cosmetic craft: 1–4px misalignments in secondary areas, easing or duration nits, icon stroke mixing, typographic niceties. |
| ✓ | Positive | Works well; keep it. |

Rate by **impact on the goal × reach (how many screens or users) × frequency (repeated actions weigh more)**. Severity reflects user impact, not how irritating something looks.

**Confidence**, required on every finding:
- **High:** clearly visible in settled frames, or measured with frame-accurate timing.
- **Medium:** visible, but intent, frequency or environment is assumed.
- **Low:** compression, low fps, a single frame, or an uncertain input time.

Low-confidence findings can't be P0 or P1 unless corroborated in two or more places.

## Finding template
```markdown
#### [P1 · High confidence] F-03 · Save gives no feedback for 2.4 s
- **Category / Check ID:** Feedback · NO-FEEDBACK (also LATENCY-ACTION)
- **Where:** Settings › Profile, "Save" button · 00:41.200–00:43.600 · frames f1236–f1308
- **Evidence type:** Measured (frame-stepped) | Direct observation | Inference | Needs verification
- **Observation (what is visible, no interpretation):** Tap indicator on "Save" at 00:41.200; button shows no pressed state; screen is unchanged until a toast appears at 00:43.600.
- **Measurement:** input→first visual response 2.40 s (±33 ms at 30 fps); threshold 100 ms feedback / 1 s attention.
- **Expected vs actual:** Expected immediate pressed state + spinner in button within 100 ms. Actual: no change for 2.4 s.
- **Principle:** Nielsen #1 Visibility of system status; response-time limits (0.1 s / 1 s / 10 s).
- **User impact:** User can't tell if the tap registered; likely double-taps (seen at 00:42.1) → risk of duplicate submissions.
- **Likely cause (inferred):** feedback rendered only after network response.
- **Recommendation:** Show pressed state on touch-down and an in-button spinner keeping the "Save" label; optimistic update if safe. · **Effort:** S · **Change level:** Component
- **Verify by:** Re-record the same tap; first visual change ≤100 ms, confirmation ≤1 s.
- **Frame:** ![F-03](assets/F-03.png)
```
**Report skeleton:**
1. YAML front matter with counts by severity, coverage % and evidence limits.
2. A provenance line (method, frames sampled, fps).
3. Executive summary, 3–5 sentences, top 3 fixes.
4. Scope, method and evidence limits, including the **Not assessable from this recording** list.
5. Timeline table (time, action, screen/state, response time, notes).
6. Findings overview table (ID, Sev, Conf, Time, Screen, Check, Finding).
7. Detailed findings grouped by UI, Design, Latency (or by screen).
8. Latency table: action, input to feedback, input to ready, threshold, verdict.
9. Cross-screen consistency table (role, values per screen, status).
10. Journey-level findings (Peak-End: worst moment and final screen).
11. What works.
12. Prioritised fixes: Quick wins, Planned, Polish.
13. Coverage ledger: screen × state as Passed, Failed, Not observed, or Not assessable.
14. Recommended next checks (things only user testing, code or assistive-technology testing can answer).

## Not assessable from a screen recording (include the relevant items in every report)
- Keyboard focus order and traps
- Screen-reader names, roles and reading order
- Alt text
- Semantic HTML or native semantics
- Haptics
- Audio cues (unless audio is recorded)
- Reduced-motion and Dynamic Type behaviour (unless recorded)
- Hover states on touch devices
- States and screens not reached in the recording
- Exact colour values or contrast (estimates only, because of compression)
- Exact pixel sizes (estimates only)
- Root causes of latency (network vs CPU vs server) without logs
- Behaviour on other devices, viewports or themes not shown
- Copy in languages not shown

## Additions for recordings
- Put the timing resolution and the input-detection method in the provenance line.
- Auto-signals you checked and dismissed go in an appendix, "Signals dismissed as noise", with one line each. This shows what was checked.
- Evidence images: cite the grid, strip or frame file with time, for example `events/E07_00-04.778.jpg @ 00:05.020`. Make extra crops with `frames --crop` when a finding needs one.

## findings.json (the source for the published page)

`scripts/render_report.py <audit folder>` turns this file into `report/index.html` (published as an Artifact),
`report/img/*.jpg` and `report/report.md`. The finding template above maps one-to-one onto these fields.

```json
{
  "title": "Product Flow Name",            // page name: a specific noun phrase, no explainer after a dash
  "subject": "One or two sentences: what was recorded and what this review covers.",
  "summary": "3-5 sentences.",
  "top_fixes": ["...", "..."],
  "timeline": [{"time": 0.0, "screen": "Landing", "change": "..."}],
  "findings": [{
    "id": "F-01", "severity": "P0|P1|P2|P3", "confidence": "High|Medium|Low",
    "title": "Plain statement of the problem",
    "check": "CHECK-ID from checklist.md",
    "screen": "Where in the product", "time": "00:41.2-00:43.6",
    "evidence": [
      {"time": 41.2, "caption": "What this frame shows",
       "marks": [{"x": 812, "y": 1290, "w": 160, "h": 64, "label": "1"}]}
    ],
    "observation": "What is visible, no interpretation.",
    "expected": "...", "impact": "Cost to the user.", "cause": "Likely cause (inferred), optional.",
    "fix": {
      "summary": "One-sentence fix.",
      "steps": ["optional", "steps"],
      "mock": {
        "caption": "Mock-up of the profile form with the fix applied.",
        "fonts": ["Inter"],
        "css": ".f{background:#fff;padding:16px;display:grid;gap:10px} .btn{background:#111;color:#fff;border-radius:999px;padding:8px;text-align:center}",
        "html": "<div class=\"f\">... <div class=\"btn chg\">Save profile</div></div>"
      },
      "changes": [{"what": "Button label", "before": "Submit", "after": "Save profile"}],
      "code_refs": [{"file": "frontend/src/features/profile/form.tsx", "line": 88, "note": "t('Submit') on the save button"}],
      "effort": "S|M|L",
      "verify": "How to check the fix worked, ideally a re-recording test."
    }
  }],
  "positives": ["..."], "evidence_limits": ["..."], "not_assessable": ["..."],
  "dismissed": ["auto-signals checked and dismissed"], "next_checks": ["..."]
}
```

Marks:
- `x, y, w, h` are pixels of the displayed frame (the size in `analysis.md`).
- Draw the rectangle tightly around the problem; the page adds the ellipse and the padding.
- Use several marks for several spots in one frame, labelled 1, 2, 3 and referenced in the caption.
- A finding about something missing marks where it should be.
- A finding about the whole screen (a theme change) may have an evidence item with an empty `marks` list.
- `time` picks the frame on screen at that moment, from the script's own frame cache.

Mock-ups (`fix.mock`):
- An HTML/CSS recreation of the affected region **with the fix applied**, shown beside the marked screenshot.
- It is rendered inside its own shadow root, so its CSS cannot touch the page and the page's CSS cannot touch it.
- Copy the product's look from the frames (or from the codebase's tokens when available). Mark every
  changed element with `class="chg"`, which draws a dashed outline.
- Plain HTML and CSS only: no `<script>` and no external images; web fonts only through `mock.fonts`. Keep it about 400 px wide and responsive.
- Use placeholder personal data, and name any guesses in `caption`.
- `mock.fonts`: Google Fonts families the mock uses (the page loads them); leave out for system fonts.
- When the code is available, put its tokens on `:host` as custom properties and use them throughout the mock.

Code references (`fix.code_refs`):
- Each entry is `{file, line, note}`, with the path relative to the workspace root.
- The page shows them under "Where in the code".
- Verify every one by printing the line before rendering.
