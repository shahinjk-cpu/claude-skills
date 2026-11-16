# How it works

Viral Video Cloner is a skill: instructions your agent follows. The rendering happens in
[ChatCut Desktop](https://chatcut.io/viralvideocloner?utm_source=github&utm_medium=docs&utm_campaign=oss_viral_cloner),
which connects to your agent as a local MCP server and runs generation in the cloud.

```text
you ──prompt──▶ agent (Claude Code / Codex) ──MCP──▶ ChatCut Desktop ──▶ cloud generation
                  │ reads the source, writes the plan        │ guides the new video with the source's motion
                  └ quotes length and credits, waits for OK  └ result lands in a ChatCut project
```

## 1. The plan

Your agent watches the source and writes a plan before anything is generated. A plan names:

- **shots**: every cut, with start and end times, and what happens in each shot;
- **subjects** or **targets**: who or what is recast, identified by role ("the skateboarder in
  every frame", "the tumbler she holds up"), and what replaces it, taken from your reference photos;
- **scene**: for motion transfer, the new place and light; for object swap in newer ChatCut versions,
  what happens in the source;
- **stays**: for object swap in newer ChatCut versions, everything that must not change;
- **constraints**: what must hold in every frame ("no text or logos", "her whole body stays in frame").

Each example in [examples/](../examples/README.md) includes the exact plan that produced it.

## 2. Two ways to recreate

**Object swap** edits the original footage. Only the people, products or outfits named in the
plan change; every other pixel stays, including the background, other people and any captions
burned into the source.

**Motion transfer** keeps only the motion. The whole frame is generated again from your reference
photos and the plan, so the place, the light and even the art style can change. Anything you give
no reference for (passers-by, the background) will only roughly resemble the source.

How the agent chooses: if the parts you didn't mention matter (a specific place, other people, a
product label you want to keep), it uses object swap. To change the place or the style, it has to
use motion transfer.

**Batch** runs the same plan several times with a different cast or product each time.

## 3. What to expect

- Moves, camera work and cut points follow the source. Fast cuts under about 0.3 seconds can drift.
- New subjects take on the source subject's silhouette and size. A lipstick held between two
  fingers becomes an odd loudspeaker; pick replacements with a similar shape.
- Large text in the source turns into garbled letters under motion transfer; small text and logos
  disappear.
- The source audio is kept. When the source has none, the result keeps the sound the model generates.
- Length: 4 to 30 seconds per recreation, cut to whole seconds.

## 4. Your own footage

When you have footage and want it cut like a reference, the agent breaks the reference down
(shot lengths and cut rhythm, transitions, caption and title styles, motion graphics, B-roll,
music, color) and applies the same moves to your material in ChatCut.
