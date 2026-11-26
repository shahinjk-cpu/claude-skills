---
name: youtube-agent-skill
description: Researches, scripts, packages, and extracts data from YouTube videos and channels. Use when extracting video transcripts and timestamps for research/RAG, writing retention-focused video scripts with 21 hook formulas, optimizing title-thumbnail pairs (CTR), creating Shorts/Reels adaptations, generating SEO metadata, or structuring video chapters.
---

# YouTube Agent Skill

Complete YouTube intelligence, content creation, transcript extraction, and growth framework inspired by `Jakeschincariol/youtube-agent-skill` and `ZeroPointRepo/youtube-skills`.

---

## 1. Video Transcript Extraction & Academic/RAG Pipeline

Extract complete spoken transcripts with timestamps from any YouTube video for research, dissertation synthesis, or RAG ingestion.

### Running the Extraction Script
Use the built-in script `scripts/fetch_transcript.py`:

```bash
# Extract full transcript to markdown with timestamps
python C:/Users/shahin.karimov/.gemini/config/skills/youtube-agent-skill/scripts/fetch_transcript.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --format markdown --output transcript.md

# Extract clean text only (for LLM context / RAG embedding)
python C:/Users/shahin.karimov/.gemini/config/skills/youtube-agent-skill/scripts/fetch_transcript.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --format text --output lecture_notes.txt
```

---

## 2. The 21 Hook Formulas (First 5–15 Seconds)

Never start a video with *"Hey guys, welcome back to my channel"*. Use one of the 21 tested psychological retention formulas:

| Category | Formula Name | Blueprint | Example |
|---|---|---|---|
| **High Stakes** | The Catastrophe | "[Worst outcome] happened, and here is how I survived it." | "My game lost \$40,000 on launch day. Here is what broke." |
| **High Stakes** | The Ultimatum | "I gave myself [Constraint] to build [Goal] or else [Consequence]." | "I gave myself 48 hours to code a 3D game or delete my channel." |
| **Curiosity Gap** | The Hidden Mechanism | "Everyone thinks [X] causes [Y], but it's actually [Z]." | "This 2-line code change doubled my app's frame rate." |
| **Curiosity Gap** | The Forbidden Knowledge | "I wasn't supposed to find this in [System/Code]." | "I reverse-engineered an Adobe app. Here is what they hide." |
| **Contrarian** | The Sacred Cow | "Stop doing [Standard Practice]. Here is what actually works." | "Stop using Redux in 2026. Use this instead." |
| **Contrarian** | The Myth Buster | "[Popular Belief] is mathematically wrong." | "Why 120 FPS games actually lag on modern monitors." |
| **Pattern Interrupt** | Immediate Action | Start mid-action without preamble. | *(Clack of keyboard, explosion on screen)* "We have 10 seconds before the server crashes." |
| **Pattern Interrupt** | The Impossible Claim | State a shocking fact, then prove it. | "This script wrote an entire research paper in 8 minutes." |
| **Transformation** | Before & After | "This was my app [Before]. 7 days later, it looks like this [After]." | "From a messy prototype to 100k downloads: Step 1." |
| **Social Proof** | The Elite Benchmark | "How [Top Company/Person] designs their architecture." | "How Google engineers structure their Flutter applications." |

---

## 3. Packaging & CTR Optimization (Title + Thumbnail Matrix)

A great title fails without a complementary thumbnail. Never repeat thumbnail text in the title.

### The Rule of Complements:
- **Thumbnail:** Captures emotional reaction or visually intriguing focal point + maximum 2–4 bold words.
- **Title:** Delivers the premise and context (50–60 characters).

### Examples:
- **Title:** *Why I Deleted My Best-Selling Steam Game*
  - **Thumbnail Visual:** Depressed developer facing red Steam analytics screen plunging to 0.
  - **Thumbnail Text:** *"IT'S OVER."*
- **Title:** *How to Build a Complete Game in Rust (From Scratch)*
  - **Thumbnail Visual:** Split screen comparing 10,000 lines of C++ vs. 200 lines of Rust with 120 FPS counter.
  - **Thumbnail Text:** *"RUST WINS?"*

---

## 4. Scripting & Retention Pacing Architecture

Structure 8–15 minute videos into a 4-beat retention curve:

1. **The Hook (0:00 - 0:30):** Deliver the promise within 15 seconds. Show the end result or peak moment immediately.
2. **The Context / Stake (0:30 - 2:00):** Why should the viewer care? What will they learn or gain by staying until the end?
3. **The Core Journey / Beats (2:00 - End - 1:00):**
   - Break into 3–5 distinct chapters.
   - Insert a **Pattern Interrupt** (b-roll, sound effect, visual punch-in, meme, or graph) every 30–45 seconds.
   - Use **Open Loops**: *"Before I show you the solution, we hit a roadblock that almost ruined everything..."*
4. **The Non-Ending Payoff (Final 60s):** Deliver the final resolution. **Never** say *"In conclusion"* or *"That's all for today"* (triggers instant drop-off). Seamlessly transition into the next recommended video card.

---

## 5. YouTube Shorts / Reels Viral Adaptation

- **Aspect Ratio:** 9:16 (1080x1920).
- **Target Duration:** 35–55 seconds (highest completion rate).
- **First 3 Seconds:** Bold on-screen caption + high-motion visual hook.
- **Pacing:** 140–160 words per minute. Cut all pauses > 0.2s.
- **Seamless Loop:** Make the last sentence flow directly into the opening sentence so the video loops invisibly.

---

## 6. YouTube SEO, Timestamps & Chapters Blueprint

Structure descriptions for maximum discoverability:

```markdown
[1-2 paragraph keyword-rich overview describing what the viewer learns]

🔗 LINKS & RESOURCES:
- GitHub Repository: [Link]
- Project Demo: [Link]

⏱️ CHAPTERS:
00:00 - The \$40,000 Mistake
01:15 - Why Traditional Setups Fail
03:40 - The Secret Rust Architecture
06:20 - Live Stress Test & Benchmarks
08:50 - The Final Fix You Can Copy

#GameDev #RustLang #Programming
```
