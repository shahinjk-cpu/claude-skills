# Recording gameplay from a Unity project

Unity Recorder (`com.unity.recorder`, 5.1.8 for Unity 6000.x) does not appear in Package Manager search
for Unity 6000.5 — install by name: `"com.unity.recorder": "5.1.8"` in `Packages/manifest.json` (or
Package Manager → + → Install package by name), then `UnityEditor.PackageManager.Client.Resolve()`.
Namespace for encoder settings: `UnityEditor.Recorder.Encoder` (`CoreEncoderSettings`).

## ProjectB: bot-played footage
Script: `<VSEKIT>/tools/unity/record_bot_gameplay.cs` (run with Unity MCP `eval`, file param).
1. `eval`: `EditorApplication.isPlaying = true` (check no dirty scenes first; domain reload follows, the
   next eval may fail once with "Invalid response format" — just retry).
2. `eval file=record_bot_gameplay.cs`: starts a 1-run BalanceBot batch (hero, strategy, meta profile at the
   top of the file) and arms Recorder: waits `WARMUP` s of game time in the Gameplay scene, records
   `RECORD` s of Game View at 1080×1920 60 fps (constant frame rate) as JPEG q95 frames, stops, exits
   Play Mode. Output: `<VSEKIT>/media/gameplay/<name>/f_0000.jpg…` → `media.assemble_sequence()` → mp4.
3. The bot isolates and restores the player's save; telemetry goes to `ProjectB/BalanceReports/` (gitignored).

## Traps found
- **Auto-pause on focus loss** (GameManager, Sprint 15.1) pauses bot runs when Unity isn't focused; the bot
  never resumes. The script resumes it each tick. A proper fix belongs in the game (skip auto-pause while
  `BalanceBotRunner.IsBatchRunning`).
- **The MP4 movie recorder is the bottleneck (diagnosed with the Unity Profiler, editor focused).**
  `WindowsVideoMedia.WriteSample` (Unity's Media Foundation H.264 encoder) blocks ~1003–1007 ms per frame
  — a timeout, not slow encoding — after the first ~100–200 frames. Short tests look fine (106–166 fps for
  ≤120 frames), long ones drop to ~1 fps. Happens at 1080×1920; likely triggered by feeding frames faster
  than real time (bot fixed-step ≈ 230 fps without recorder).
  Measured alternatives (1080×1920, bot running): **JPEG sequence 28 fps sustained (900 frames)**,
  PNG sequence 10 fps (CPU-bound compression). JPEG q95 looks clean; ffmpeg NVENC assembles 15 s in ~5 s.
  → `record_bot_gameplay.cs` records JPEG; then `vsekit.media.assemble_sequence(folder, out.mp4, 60)`.
  Disk: ~12 MB per second of 1080×1920 JPEG footage at 60 fps.
- Not the cause (ruled out): window focus, game/bot load (bot alone ≈230 fps), Mono heap size (~1.15 GB is
  this project's baseline), the author's background GPU jobs.
- Unfocused editor: Unity MCP `set_auto_tick` forces editor ticks while unfocused; untested for capture.
- Profiling recipe: `profiler_record` (frames 60, areas CPU) → `profiler_session` (confirm) →
  `profiler_markers` — the top self-time marker names the culprit.
- `ImageRecorderSettings.OutputFile` with `<Frame>`: build the path by string concat — `Path.Combine`
  throws "Illegal characters in path".
- The bot's run limit is wall-clock; with a slow editor it ends early — `maxRunMinutes` is raised in the script.
- `AudioManager` is muted for bot runs — record picture only, add music/SFX in the edit.
- UI language follows the system/locale (footage came out with Russian HUD).
