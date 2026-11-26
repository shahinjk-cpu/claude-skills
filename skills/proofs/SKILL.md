---
name: article-copy-edit
version: 1.5.3
allowed-tools:
  - Read(/${CLAUDE_PLUGIN_ROOT}/**)
  - Bash(python3 ${CLAUDE_PLUGIN_ROOT}/shared/review_page/review_page.py *)
description: Use when the user hands you copy-edit feedback or proposed line edits for an article or page and wants to approve each change before the file is touched, or asks to go through copy together. Differs from design-review; this judges words and claims, with a standing compliance audit, not layout.
---

# Article Copy-Edit Review Tool

A human-in-the-loop process for applying copy-edit feedback to an article or page. Instead of applying edits blind, or narrating each one in chat, build an interactive review page the user reads and clicks through, then apply only what they accepted.

**Results first.** Nothing matters more than a result the user wants. Save tokens by cutting waste, never by cutting a check, an option or a revise pass the result needs (full text: `../../reference/house-rules.md`).

## Why this exists

Artifacts can't send live clicks back into the conversation; there's no channel from a button in the rendered page back to Claude. So the loop is: build a review page, the user picks a decision on each item (optionally with a comment), clicks "Copy My Decisions", pastes the plain-text summary back into chat, and Claude applies exactly the accepted edits (with any comment-driven tweaks) to the real file.

## When to use

The user hands you copy-edit feedback (their own, or a third party's) for a specific article or page and wants to go through it deliberately rather than have you apply it all at once. Signals: they say "let's review this together," paste a batch of proposed edits, or ask for something like this tool by name.

Its sibling, `design-review`, runs the same loop for visual and layout changes. Both use the same four decision states and the same "Copy My Decisions" export.

## The process

### 1. Identify the exact target file and read it in full

Cross-reference quoted "Original" text in the feedback against the real file to find the exact file. Don't guess from a title alone; read enough of the file to confirm every quote actually appears verbatim. Get exact current line numbers and context for each edit location. You need them both for the review page and for applying changes later.

### 2. Run the Claims & Compliance audit: mandatory, always on, first section

First, find out what is risky in this project's field. Look in the project's notes (`CLAUDE.md`) and any existing style or compliance guidance. If neither says, **ask the user once**: "What kinds of claims are risky or regulated in your field?" Health and wellness claims, and environmental or product-safety claims, are only examples. A financial, legal, food, or software site has different ones. Keep the answer in the project's notes so you don't have to ask again.

Then, before turning the user's own feedback into items, do a fresh pass over the **entire current article or page** (not just the lines the feedback happens to touch). Check the project's list of risky claims first, then these general risks:

- **Guarantee or certainty language** ("ensures," "guaranteed," "you only pay for the results you achieve") without a "results vary / not guaranteed" qualifier nearby.
- **Diagnosis, cure, or professional-authority implications**: wording that makes the author or business sound like it diagnoses, treats, or certifies something it has no standing to. Copy should never blur that line.
- **Outcome-tied pricing**, or claims that imply a specific measurable result is promised.
- **Before/after or results content** (photos, case studies, testimonials) with no "individual results vary" or "not typical" disclosure nearby.
- **Missing or unclear disclosure where one is legally required.** In particular, flag any page that recommends products through affiliate links but lacks the disclosure the FTC requires (a clear statement that the site may earn a commission), even if fixing it is out of scope for this particular review.
- **Anything that would read, in isolation, as a claim the page's own disclaimer (if it has one) contradicts.** Titles and headings are the highest-risk spot, since they're what gets pulled into browser tabs, social previews, and search results.

This audit runs **regardless of whether the user's feedback mentions compliance at all**. It's a separate, standing check, not something triggered only when a recommendation happens to raise one.

Findings become their own numbered items in a section titled **"Claims & Compliance"**, always rendered **first**, above the copy-edit and recommendation sections. Include it even if it's empty: show a plain "No compliance concerns found in this pass" state rather than omitting the section, so its absence is visibly a checked box, not a skipped one. Same card structure as every other item (Reason, Recommended/Not Recommended, four decision buttons). A compliance finding being "Recommended" means recommended to fix.

### 3. Turn the feedback into discrete numbered items

Each item is one self-contained change:
- **Line edits** (existing text to proposed text): pull the exact current text from the file, not from the feedback's possibly paraphrased quote of it.
- **New additions** (a whole new section, a call to action, an intro paragraph): "original" is a short italic note describing what's there today (usually "nothing"), "edit" is the proposed new content, and a `where` field says where it would go.
- **Alternatives that conflict** (e.g., two different proposed titles for the same H1): present both as separate items, but say explicitly in each one's reason that accepting it supersedes the other.
- **Non-visual changes** (alt text, meta tags): still get a card, but show the before/after as `<code>` snippets instead of rendered prose.

Give every item, edit or addition alike:
- A **Reason**: why this specific change is an improvement (or why it's proposed despite reservations).
- A **Recommended / Not Recommended** badge: your own honest editorial judgment, independent of whether you're going to present the item at all. If you have a real reservation (compliance risk, factual risk, conflict with established site copy elsewhere), mark it Not Recommended and say why in the reason. Don't silently omit it, and don't silently soften your opinion to make the badge match what you think the user wants to hear. The point of the badge is that the user can see your take before they decide, and overrule it.

### 4. Build the review page with the shared builder

**Needs the whole plugin.** This skill reads shared files at `../../reference/` and `../../shared/`, relative to its folder. If they are missing, the skill was copied on its own: install the whole plugin (`/plugin install proofs@proofs`) rather than recreating them.

Write the content; the builder writes the page. Read `../../reference/review-page.md` first: it documents the spec and the command, `python3 ${CLAUDE_PLUGIN_ROOT}/shared/review_page/review_page.py .proofs/copy-edit/spec.json --out .proofs/pages/<edit-name>.html`, with `"decisions": "copy-edit"`. Do not hand-write the page's JavaScript. Follow any design guidance your environment provides for published pages: "utilitarian but polished," not a landing page. Fill `project` with `name`, `session` and `repo`, taking the session name the way the `working-log` skill does (the session's own name, else one named for the work, kept for the life of the page): the page's header shows the proofs mark, this skill's name, the project and the session, so the user can match the page to its session at a glance.

- **Reuse the target page's own design system** (the spec's `css` and `vars`). Don't invent a palette; pull colors and type straight from the article or page you're editing, and reuse the site's own before/after colors for "original" and "edit" if it has an established pairing, working in both light and dark mode. If the site themes through CSS variables or tokens, take the light/dark values from those same variables.
- **Highlight word-level diffs**, not just whole-paragraph swaps: wrap the changed spans in `<del>`/`<ins>` inside `.rp-panes`.
- **Sections in this order:** Claims & Compliance (always first, always present; when empty its `empty_html` says "No compliance concerns found in this pass"), then Copy Edits, then Proposed Additions & Recommendations.
- **Each item:** a `label` (and `location`), `recommended`, `body_html` holding an "Original" pane and an "Edit" pane in the page's real typography, and `reason_html`. Non-visual changes (alt text, meta tags) show `<code>` snippets in the panes.
- **The Original and Edit panes always hold the literal, verbatim text, never a paraphrase or a description of the change.** "Reframes the argument around cost instead of speed" is a summary for the Reason block; the Edit pane needs the actual sentence a reader would see if it shipped. This applies even when the source feedback only describes a change in prose: write out the real replacement text yourself. A user was once left unable to act on a "Not Recommended" edit because the pane summarized what changed instead of showing it.
- **Four decision states, not two-plus-a-modifier.** Accept/Deny with an optional comment is ambiguous: Claude would have to *infer* whether a comment means "ship this, but tweak it" or "not yet, try again." The preset makes that a button:

  | Button | Exports | Comment box | Meaning |
  |---|---|---|---|
  | ✕ Keep Original | `DENY (Keep Original)` | optional | Reject the change outright. |
  | ✓ Use Edit | `ACCEPT (Use Edit)` | optional | Ship the proposed edit exactly as shown. |
  | ✓ Approve with Comment | `ACCEPT WITH COMMENT` | opens, expected | Ship it, modified per the comment. The comment is a change instruction, not a footnote. |
  | ↻ Request Revision | `REVISE` | opens, expected | Don't ship anything yet; expect a follow-up round on this item. |

- **The export's first line names the page**, because pasted decisions arrive in chat with no other context, and across a review queue a bare `1. ... — ACCEPT` is ambiguous. The builder writes the bracketed title:
  ```
  [Pricing Page — Copy-Edit Review]
  12. New — Introduction to the Method — ACCEPT WITH COMMENT — COMMENT: swap "proprietary" for "our own"
  13. Alternate — SEO-Optimized Title — DENY (Keep Original)
  14. Whole page — missing disclosure — REVISE — COMMENT: don't call it "not typical," I don't want to imply that
  ```

Deliver the page as "Where the page goes" below says (with `artifact`, that means publishing it with the `Artifact` tool). Redeploy to the same file path when you add fields or fix bugs; don't mint a new URL for revisions the user is already looking at.

**Verify before publishing, on every revision.** The build runs its own check (script syntax, card and button counts). Run `--smoke`. If it reports Playwright missing, run the one-line install it prints (it uses your installed Google Chrome and downloads no browser), then run `--smoke` again; if it still cannot run, say on the page and in chat that the self-check did not run. Then look at the page: every item rendered, the panes read correctly. Only publish after that.

### 5. Applying the decisions

When the user pastes back the copied summary, match items by number.

- **`ACCEPT`**: apply the edit exactly as proposed.
- **`ACCEPT WITH COMMENT`**: apply the edit, but the comment is a change instruction that modifies it first. Don't ship the edit verbatim and separately guess at the comment; read the comment, work out what the final text should be, and apply *that*.
- **`DENY`**: leave the file untouched. A comment here is a note or reason, not an instruction to act on.
- **`REVISE`**: leave the file untouched *for now*. The comment is feedback for a follow-up round on this specific item (see below). Don't apply anything from it yet, and don't treat it as an implicit accept.
- **`PENDING`**: not reviewed yet; leave untouched, don't chase it.

Note anything you skipped and why. Verify and commit following the project's own notes (`CLAUDE.md`). The review tool changes nothing about how the actual file edit gets verified and shipped.

### 6. Follow-up rounds on `REVISE` items

When one or more items come back `REVISE`, build a new round rather than silently iterating in chat. The same human-in-the-loop principle applies to round 2 as to round 1.

- **Scope the new Artifact to only the still-open items, but "still open" means every item without a final decision, not just the ones marked `REVISE`.** Don't re-show items already resolved (`ACCEPT`, `ACCEPT WITH COMMENT`, `DENY`): they're already applied or settled, and re-litigating them wastes the user's attention and risks a stray click undoing a done decision. But a `PENDING` item from the prior round (never decided at all, just not part of that round's revision batch) is not resolved either. Dropping it when you rescope to "the items sent back for revision" silently deletes the user's only path to ever deciding it. Carry every non-final item forward into each new round, not just the ones explicitly revised. If only one item is open, the whole page is one card.
- **Carry the history forward on each card.** Show the prior round's proposal, clearly labeled ("Round 1 (requested revision)"), with the user's own revision comment quoted or summarized so they have full context without scrolling back through chat. Then show the new proposal, labeled "Round 2 proposal" (increment further if it goes another round). Don't make the user re-explain what they already told you.
- **Republish to the same Artifact URL**, per the "same file path" guidance above, for every follow-up round. Put the history in each item's `history_html`.
- **Re-run the verification step** before every republish. A smaller page is not a lower-risk page.

## Where the page goes

Before you publish or save the page, read `../../reference/where-the-page-goes.md` (the path is relative to this skill's folder). The project's `PROOFS_PAGES` setting picks artifact, file or wifi, and that file says what each means and how copy buttons must fall back.
