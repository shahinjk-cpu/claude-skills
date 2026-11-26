# Scoring guide

The rules live in the user's `profile.md`. This file explains how to apply them consistently.

## Read the whole ad before scoring
- Separate **must have** from **nice to have**. Only must-haves cost points.
- Years of experience: "3+ years or equivalent", "ideally", or "a plus" means it's open: score it under level fit. It's a hard fail only under the profile's rule (a senior title, or ≥ 3× the user's years with no "or equivalent").
- Look for the real workload (`80–100%`, `Teilzeit`, `temps partiel`), the real location (office vs "remote within country"), and the deadline.
- Vague experience counts as years: "several years", "mehrjährige Erfahrung", "plusieurs années", "solid experience" ≈ 3+ years. "First experience", "erste Berufserfahrung", "première expérience" ≈ 0–1 year.
- Degree wording decides whether there's a penalty. "Required", "exigé" or "zwingend" is a requirement. "Preferred", "souhaité", "idéalement", "von Vorteil", "or equivalent", or "self-taught welcome" is **not**: no penalty at all.
- 10/10 is allowed when every part is a full match. Don't cap scores out of habit.
- Agencies often hide the employer. Note "via agency" in the tracker.

## Be consistent
- Write a one-line reason for every score: `why · missing`.
- Score two similar offers the same way: before recording, compare with a past tracker row for a similar role.
- When unsure between two scores, take the lower one and say why. A false 7 wastes an application; a false 6 is just one line in `seen.md`.

- Evergreen roles: some ads stay open for years and get "re-posted" with a fresh date. The window uses the real first-published date, so a proven-old ad goes to `seen.md` as "old ad". The only exception: target-company roles listed on the first run, which show "open since …".

## Examples (generic profile: junior web developer, 1 yr, Python/TypeScript/React, French C2, English B2, search area Lyon + remote-from-France, no Master's degree)

| Ad | Role | Stack | Level | Place | Lang | Score | Reason |
|---|---|---|---|---|---|---|---|
| Junior Full-stack Developer, React/Node, Lyon hybrid | 2 | 2 | 2 | 2 | 1 | 9 | Title + React match, local · missing: Node |
| Python Developer, 2+ yrs or equivalent, Lyon | 2 | 3 | 2 | 2 | 1 | 10 | Stack match, "or equivalent" |
| Python Developer, 2 yrs, Lyon | 2 | 3 | 1 | 2 | 1 | 9 | Stack match · missing: 2 yrs |
| Python Developer, 3+ yrs, Lyon | — | — | — | — | — | 0 | Hard fail: 3× the user's 1 year, no "or equivalent" |
| Backend Engineer, Java/Spring, Lyon | 2 | 0 | 2 | 2 | 1 | 6 (capped) | Adds up to 7, but 0 on stack: capped at 6 |
| Frontend Developer, React, remote "EMEA" | 2 | 3 | 2 | 1 | 1 | 9 | React match · check remote country |
| Software Engineer, React, no years stated, remote EU | 2 | 3 | 1 | 2 | 1 | 9 | React match · level unstated |
| Full-stack Engineer, React, "mentor juniors, own architecture" | 2 | 3 | 0 | 2 | 1 | 6 (capped) | Leadership required: Level 0 caps it |
| Senior Backend Engineer, 7+ yrs, Go | — | — | — | — | — | 0 | Hard fail: senior title |
| Data Scientist, Master's degree required | — | — | — | — | — | 0 | Hard fail: Master's degree required |
| Junior Developer, German C1 required, Munich | — | — | — | — | — | 0 | Hard fail: German C1 (user has none) |

Rule: an offer scoring 0 on Role fit, Stack & skills or Level fit can't be kept, whatever the total: cap it at threshold − 1. This is what stops mid-level and wrong-stack roles from flooding a junior's tracker.
