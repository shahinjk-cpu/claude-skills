# Writing for someone who has never coded

The reader is new to this codebase and maybe to coding. They learn by zooming in and out, pressing Play, and reading one box at a time. Every sentence should leave them knowing something true and specific that they didn't know before.

## Read before you write

- Read the code of the box. For a function, also skim its callers and what it calls. Names lie: `validate()` might also save to the database.
- Write what it actually does in this project, not what such functions usually do.
- If the purpose is unclear after reading, write what you can see ("Builds the email text; it is called from two places in the checkout") and say what is uncertain. Never invent behaviour, numbers or history.

## The three fields

- **what (one sentence):** the job, in everyday words. "Turns an order into the short label shown in lists."
- **does (two to four sentences):** the steps, in order, with the interesting rule or decision. "Orders over 10 are 'big'; the rest are 'small'. The list page uses the label to colour the row."
- **example:** one concrete case with real-looking values. Mark made-up values as made up.

## Plain words

- Explain each technical word the first time it appears in a box, in the same sentence, or link it with `[[word]]` and add it to the glossary. "A [[handler]] (the function the server runs for one web address)."
- Use short sentences, active voice and everyday comparisons that are accurate: "like a receptionist routing calls" works for a router. Avoid comparisons that need their own explanation.
- Numbers stay numbers. Name real files and functions in backticks.
- Avoid filler ("This function is responsible for..."). Start with the verb: "Loads every order from the database."

## Beginner layer

- **in / out:** what goes in and what comes back, as things a person could hold. "One line of text, like 'Hello'" → "an audio clip and the time each word starts".
- **to:** the purpose as a phrase that completes "X asks Y ___": "to label an order". Keep it short; it appears in sentences, wire labels and story scenes.
- **tag:** 2 to 4 words for the wire label: "label it", "get orders", "check SEO".
- **Play steps:** one step per box, in the order things happen. Each step says what this box does in this run and why it is next. 4 to 8 steps per area.

## Stories

- Choose a world that fits the project, and keep it consistent: town, kitchen, hospital, factory, school or spaceship. The default is a town. Neighbourhoods are areas, buildings are files and people are functions.
- Hand-write the overview story: 6 to 9 scenes showing how the areas work together, ending with what the project delivers to its users.
- Bubbles are what a character would say, one sentence. Captions state the fact in under about 14 words. Envelopes carry the real data, like `"neural-network"` or `a list of 12 lines`.
- Quiz questions test the flow ("Who does Main ask for the lines?"), not trivia. Make the wrong options plausible.
- If a building's generated story reads flat (all "My job: ..."), hand-write that one.

## How much to explain

Overview first:
1. Every area, group and file.
2. Entry points (code that runs by itself, `main`, route handlers, CLI commands).
3. Functions with many callers.
4. Whatever the user asked about.

Then stop and tell the user what is covered and what is left ("all 9 areas and 140 files explained; 210 of 1,300 functions; ask me for any area"). On request, explain a section fully: read it, write it, `--stamp`, rescan.
