# AI-scored and async interviews

More screens are now scored by software (audio/video bots, WhatsApp interviews, one-way video). They score structure, completeness and specifics. Adaptive bots ask follow-ups until they get numbers.

## Answer rules
1. **First sentence = the direct answer** to the exact question. Then 2–3 supporting points. Stop.
2. **Answer every part.** If the question has three parts, say "Three things: first…, second…, third…".
3. **60–90 seconds per answer.** No restarting sentences: pause silently instead of filler words.
4. **1–2 comparative numbers per answer:** baseline → result, before → after, test vs. production. Take them from the numbers bank in `stories.md`. Never invent one: say "I don't have the exact figure; it was roughly…" only if the candidate confirmed the range.
5. **Cover how you know it works in production:** the metric, how it's monitored, what happens to low-confidence or failed cases.
6. Close with the business result, not the technique.

## Before the interview
- Run a mock: Claude asks likely questions one at a time and scores each answer against these rules.
- Practise the pitch and top stories out loud 3× with a timer.

## After
Log the questions asked and any feedback in `interview/<company>.md`, and add a `stage` event (`data.format`, `vendor`, `scores`).
