---
name: music-lyrics-generate
description: Write song lyrics in any genre and language that are singable, specific and true to their genre. Use when asked to "write lyrics", "generate lyrics", "create song text", "write a song", "write verses", or "create lyrics for track". Universal craft rules are binding; genre profiles are defaults that the song may depart from for a reason; the language section adjusts syllables, rhyme and stress for Russian, Spanish and other languages; the output is the song text only.
---

# Song lyrics

## How to read this skill

- **Section 1 — craft — is binding** for every song, in every genre and language.
- **Section 4 — genre profiles — are defaults**, not laws: where the song is better for departing from
  its genre's default, depart, and keep the reason in the summary (not in the lyric file). The
  principle that holds across genres: conform to the genre on most parameters and deviate meaningfully
  on one or two (optimal distinctiveness).
- **Numbers are orientation.** Syllables per line, rhyme density and repetition levels below come from
  studies of English-language charts (Parada-Cabaleiro et al., 2024, *Scientific Reports*, 353,320
  songs; Varnum et al., 2021, *PLOS ONE*, 14,661 Billboard songs; Berger & Packard, 2018,
  *Psychological Science*: topically atypical songs rank higher). They describe what hits did on
  average; they are not targets to write to, and for other languages they are only a rough guide
  (section 3).
- **Commercial pull is an option, not the goal.** A compact, repetitive hook is the pop default; a
  ballad, a narrative or an art song is judged by whether it works as that.

## 0. Inputs

1. The genre (and subgenre), the language, the mood, the theme or story, and the performer's voice
   come from the request, the recipe or the project (e.g. `MUSIC_PRIMARY_GENRE`,
   `MUSIC_LYRICS_LANGUAGE`, `MUSIC_STYLE`).
2. **When the person has described the story** (two or more of: a character, a setting, a time, a mood,
   concrete details, constraints), write it — do not offer alternative plots and do not ask again.
   Offer ideas only when asked, or when the request is a bare one-word topic.
3. **When the genre is missing**, ask once — unless the mood and the theme together already determine
   it, in which case state the genre you chose in the summary.
4. **A genre not in section 4**: build its profile from the nearest family (e.g. *bachata* from
   Latin/Reggaeton + R&B, *synthwave* from EDM + Pop, *shanson* from Folk + Outlaw/Traditional),
   adjust what the genre plainly does differently, and name the assumption in the summary.
5. **A fusion**: the primary genre is the base; take one or two elements of the secondary genre on
   purpose.
6. **Conflicting asks** ("simple Americana", "dense-vocabulary pop"): say there is a tension, choose a
   resolution, and say which.

## 1. Craft — binding for every song

1. **Singable.** No tongue-twisters, no unnatural stress, no consonant pile-ups unless the effect is
   the point. Read every line aloud in the rhythm it will be sung.
2. **The hook is the most memorable phrase in the song**, and every section leads toward it or away
   from it on purpose.
3. **No filler.** Every line serves the story, the mood or the hook. A line that exists only to rhyme
   is rewritten.
4. **One image system.** Images and metaphors belong to one world and reinforce each other across
   the song (a train song: rails, coal dust, sparks, steel, smoke), not a string of unrelated
   metaphors.
5. **No clichés.** Avoid stock images ("tears like rain", "heart on fire", "broken wings"); find the
   specific image that belongs to this song's world.
6. **Verses advance.** Verse 2 raises the stakes, adds information or shifts the view; no verse
   restates another.
7. **Arc** (when there are two or more verses and a bridge):
   - Verse 1 sets the world; Verse 2 develops it; the bridge carries the peak — a confession, a
     reveal, a shift (I → we, present → past, defiance → vulnerability, concrete → philosophical);
     the final chorus says the same words with the weight the bridge gave them.
   - Without a bridge, the last verse still turns — a twist, a new detail, a change of temperature.
   - Shapes that work: ascending (quiet → peak → powerful last chorus), descending (defiant →
     vulnerable → resolved), circular (the opening image returns, changed).
   - An outro resolves or stays open on purpose; it never just fades lyrically.
8. **Mirroring.** Corresponding lines of different verses keep the same stress pattern, so the same
   melody carries both.
9. **Phonetic texture** where it helps: alliteration for drive, assonance for flow, consonance for
   percussive texture; plosives (b, d, g, k, p, t) for punch, fricatives and sibilants (f, s, sh, v, z)
   for flow and atmosphere. Lines that anchor rhythm (pre-chorus, hook transitions) use sound as
   deliberately as meaning.
10. **Synthetic vocalists** (Suno, Udio and the like) stumble on these; avoid them:
    - three or more negations in a line (at most two, and only when the vernacular calls for it);
    - a mid-line em dash or direct speech inside a line — use a line break or narrate instead;
    - more than one comma in a line — one caesura at most;
    - three or more unstressed function words in a row ("for no Crown Vic", "on the dam I made");
    - language-specific hazards in section 3.
11. **The performer's name is not a tag in every song.** Use it in an intro, outro or ad-lib only when
    it is justified: a debut or branding track, a genre that expects it (some trap and drill), a
    collaboration that needs credit, or when asked.

## 2. Show and tell

- **Show** — emotion through concrete, observable detail — is the default where the genre lives on
  imagery: country (all kinds), folk, Americana, rock, indie, blues, narrative hip-hop.
  - Instead of "I'm lonely": "empty chair, cold coffee, the clock ticks on the wall".
  - Instead of "I'm angry": "knuckles white around the wheel, jaw set like a vice".
- **Tell** — a direct statement — is the convention, not a fault, where the genre speaks plainly: pop
  choruses, EDM, R&B and soul confessions, gospel, punk slogans, hip-hop boasts and anthems, K-pop
  hooks, reggaeton chants. "I run this city" is the right line there; rewriting it into imagery
  weakens it.
- Most songs mix: concrete verses, direct chorus. Imagery-led genres keep a high sensory density
  (most lines earn their place through specificity); direct genres carry fewer images and stronger
  statements.
- **Kinetic imagery** — lines that imply movement, sound or touch — is the strongest kind in narrative
  genres.

## 3. Language

Most numbers in this skill were measured on English. This section says what changes in other
languages; it binds wherever it applies.

### Register, not reading level

"Grade 2.9 / 3.3" are English Flesch–Kincaid levels and do not transfer: Spanish and Russian have
their own adapted formulas (Fernández Huerta 1959 and Szigriszt-Pazos 1993 for Spanish; Oborneva 2006
for Russian), on other scales. Set the register in words — conversational, simple, literary, archaic
— as each genre profile does, in every language.

### Syllables are sung syllables

- Syllable targets are a property of the melody, not of the language. The same melody holds fewer
  words in a language with longer words (in parallel fiction, Russian averages about 3.29 syllables a
  word, English about 2.97).
- **Spanish**: count with *sinalefa* — a vowel ending a word and a vowel starting the next merge into
  one syllable (not across a pause, and not between two stressed vowels). The line's last stress
  changes the count against the *llana* baseline (stress on the second-to-last syllable): an *aguda*
  ending (last-syllable stress, or a final monosyllable) counts one more, an *esdrújula* ending one
  less. A melody's melismas can override this — fit the tune, then check.
- **Russian**: count vowels; there is no sinalefa in normal singing.
- **English**: as written; contractions and elisions ("'cause", "gonna") are legitimate fitting tools.

### Rhyme follows the language

- **English**: perfect and slant (near) rhyme; slant is the modern pop and indie default.
- **Spanish**: *consonante* (every sound from the last stressed vowel matches) or *asonante* (only the
  vowels match). *Asonante* is freer and is the popular and traditional default; contemporary pop
  accepts both.
- **Russian**: rhymes are classed by where the stress falls — masculine (last syllable), feminine
  (second-to-last), dactylic (third-to-last), hyperdactylic (further) — and as exact or inexact.
  Rhyming lines share the ending type (masculine with masculine), so the melody's phrase endings
  match. Inexact rhyme is accepted in song, especially in rap and indie.
- A rhyme always runs from the last stressed vowel; a rhyme that needs a wrong stress is no rhyme.

### Authenticity is the scene's own language

Vernacular markers belong to a scene in a language: AAVE and Southern contractions are markers of
American hip-hop and country, not of a Russian or Spanish song. Use the slang, dialect and references
of the scene the song lives in, in its language — never translated English markers.

### Stress for synthetic vocalists

- **Russian**: stress is mobile, and synthetic vocals can stress the wrong syllable while sounding
  fluent. Always write «ё». Mark the stressed vowel with an acute accent (´) in homographs (за́мок /
  замо́к), rare words and names. No vendor documents a stress notation, so check a short verse and
  chorus before a full song (stress tools such as RUAccent can propose the stresses).
- **Spanish**: correct tildes are the written stress — never drop them.
- **Any language**: avoid a line whose rhythm depends on an unusual stress of a common word.

## 4. Genre profiles (defaults)

Each profile gives: rhyme · form · register · repetition · syllables per line · hook · point of view
· themes · valence · authenticity · show/tell. Depart where the song is better for it (see "How to
read").

### Pop
- **Rhyme**: ABAB; slant over perfect; different schemes in verse and chorus.
- **Form**: verse–chorus–verse–chorus–bridge–chorus; the first chorus early (around 40–50 s); a
  chorus-first opening is common; 3–4 kinds of section.
- **Register**: conversational; sound over meaning — pick the word that sings.
- **Repetition**: very high; three or more choruses; a "glue" line shared across sections.
- **Syllables**: about 6–10; iambic patterns.
- **Hook**: the title, repeated in the chorus. **POV**: I/you; the chorus tightens to direct I/you.
- **Themes**: love and relationships, self-empowerment, sensuality — universal and relatable.
- **Valence**: mixed; bittersweet endings land well. **Show/tell**: verses show, chorus tells.

### Hip-hop / rap
- **Rhyme**: dense — internal and multisyllabic rhymes, several per line; moderate complexity reads
  best.
- **Form**: intro → hook → verse (12–16 bars, 8–12 in modern style) → hook → verse → hook → outro.
- **Register**: by subgenre — trap minimal, conscious/lyrical rich.
- **Repetition**: hook-driven; the hook repeats; verses do not.
- **Syllables**: about 10–13, set by flow and tempo.
- **Hook**: simple and chantable; title-repetition or a phrase. **POV**: first person; direct address to
  rivals, listeners, lovers; boast and narrative modes.
- **Themes**: introspection, ambition, wealth, struggle, social commentary, place.
- **Valence**: the widest range of any genre. **Authenticity**: the scene's vernacular and lived
  detail (AAVE in American hip-hop; the local scene's slang elsewhere). **Show/tell**: boasts tell,
  stories show.

### Drill / phonk / trap
- **Rhyme**: dense, repetitive end-rhymes; ad-libs as punctuation.
- **Form**: hook–verse–hook, short; phonk often loops a hook over a sample.
- **Register**: minimal, slang-heavy, menacing or hypnotic. **Repetition**: high in hooks.
- **Syllables**: drill slides and triplets — fit the flow, not a count.
- **Hook**: a short chant or a tag; performer tags and ad-libs are part of the style (rule 1.11).
- **Themes**: street, rivalry, money, night, speed (phonk: drift, nostalgia, atmosphere).
- **Show/tell**: tells, in images of the street.

### R&B / soul
- **Rhyme**: ABAB or AABB, loose; melody leads.
- **Form**: verse–pre-chorus–chorus with a bridge; room for runs and ad-libs.
- **Register**: conversational, sensual, confessional. **Repetition**: moderate-high in choruses.
- **Syllables**: flexible; leave space for melisma — fewer words, longer vowels.
- **Hook**: a phrase the voice can bend. **POV**: I/you, intimate.
- **Themes**: desire, devotion, heartbreak, longing, self-worth.
- **Valence**: warm to aching. **Show/tell**: tells feelings directly, shows the room they happen in.

### Rock / metal
- **Rhyme**: ABAB or AABB, end rhyme; less internal rhyme than rap.
- **Form**: verse–chorus–verse–chorus–bridge–chorus; a solo at the bridge; progressive styles go
  through-composed.
- **Register**: moderate-high; metal carries genre vocabulary (darkness, defiance, myth).
- **Repetition**: low (metal the lowest of all); the riff may be the hook.
- **Syllables**: about 7–10 (progressive 9–12+); thrash and death metal fast, doom stretched.
- **POV**: first person for struggle; third person for myth and history. **Themes**: rebellion,
  freedom, existential questions; metal: dystopia, battle, the dark; power metal: myth and fantasy.
- **Valence**: dark to defiant. **Show/tell**: shows.

### Punk
- **Rhyme**: simple AABB; blunt. **Form**: short verse–chorus, fast, often under three minutes.
- **Register**: plain, sardonic, slogan-ready. **Repetition**: high — gang-vocal choruses.
- **Syllables**: short, shouted lines. **Hook**: a slogan. **POV**: I and we, against them.
- **Themes**: anger, boredom, politics, alienation, friendship. **Show/tell**: tells.

### Indie / alternative
- **Rhyme**: slant, assonance, or none where prose flow serves better.
- **Form**: free — through-composed, no chorus, long tracks, dynamic shifts.
- **Register**: moderate-high, literary; wordplay, cryptic and surreal images accepted.
- **Repetition**: low; hooks may be textural rather than lyrical.
- **Syllables**: irregular; enjambment welcome. **Hook**: optional; the title may appear once or never.
- **POV**: deeply first person, particular rather than universal. **Themes**: self-discovery, alienation,
  identity, disillusion. **Valence**: bittersweet, ambiguous. **Authenticity**: real places, names and
  objects. **Show/tell**: shows.

### Folk / singer-songwriter
- **Rhyme**: ABCB ballad forms; near rhyme accepted. **Form**: strophic, verse–refrain, or a story in
  verses.
- **Register**: plain but exact. **Repetition**: a refrain, not a big chorus.
- **Syllables**: steady, speech-like. **Hook**: a refrain line or an image. **POV**: first person or a
  told story.
- **Themes**: place, work, family, history, protest, love. **Show/tell**: shows.

### Blues
- **Rhyme**: AAB — a line, the line again (often varied), a rhyming answer.
- **Form**: 12-bar verses, sometimes 8- or 16-bar. **Register**: plain, earthy, double meanings.
- **Repetition**: built in (the repeated A line). **Hook**: the turn-around line.
- **Themes**: trouble, love gone wrong, travel, work, hard luck met with wit.
- **Valence**: sorrow with humour. **Show/tell**: both — states it, then proves it with a detail.

### Gospel / worship
- **Rhyme**: simple AABB or ABAB. **Form**: verse–chorus with a rising vamp or tag repeated with
  intensity.
- **Register**: plain, scriptural imagery. **Repetition**: high — the vamp builds by repetition.
- **Hook**: a short declaration or praise line (a mantra hook). **POV**: I/we addressing God, or
  testimony.
- **Themes**: faith, deliverance, gratitude, hope. **Valence**: rising to joyful. **Show/tell**: tells.

### Electronic / EDM
- **Rhyme**: minimal; phrase repetition replaces rhyme. **Form**: verse → riser → drop; lyrics are
  short phrases that loop.
- **Register**: minimal; non-lexical sounds ("oh", "yeah") are allowed.
- **Repetition**: extreme; the drop is the main hook. **Syllables**: about 4–8, on the beat grid.
- **POV**: I or a collective "we"; many tracks need none. **Themes**: euphoria, freedom, the night,
  togetherness. **Show/tell**: tells, chantably.

### Lo-fi / chill
- **Rhyme**: loose ABAB/AABB, incidental. **Form**: short loops, 2–3 minutes, no bridge.
- **Register**: simple, quiet, honest. **Repetition**: moderate — sustains a mood.
- **Themes**: loneliness, nostalgia, anxiety, comfort. **Valence**: melancholic to cosy.
- **POV**: first person, confessional. **Show/tell**: small concrete details, softly told.

### Reggae / dancehall
- **Rhyme**: AABB, chantable; patois where the scene uses it. **Form**: verse–chorus; dancehall verses
  are toasted, rhythmic.
- **Register**: plain, spiritual or street. **Repetition**: high in choruses.
- **Themes**: love, resistance, faith, unity, party (dancehall). **Show/tell**: tells, with images of
  place.

### Latin pop / reggaeton
- **Rhyme**: *asonante* or *consonante* (section 3); end-rhymed couplets; rap-influenced in reggaeton.
- **Form**: intro–verse–pre-chorus–chorus (*coro*)–verse–chorus, often with a rap verse; the chorus
  early.
- **Register**: conversational, regional slang (Puerto Rican, Colombian…); Spanglish where the scene
  uses it.
- **Repetition**: high; a chantable *coro*. **Syllables**: counted with *sinalefa*; dembow rhythm
  rules the phrasing.
- **Hook**: a short phrase or the artist's tag. **POV**: I/you, seductive or defiant.
- **Themes**: desire, nightlife, heartbreak, confidence. **Show/tell**: tells.

### K-pop
- **Rhyme**: loose; Korean verses with English hook phrases. **Form**: verse–pre-chorus–chorus–rap
  break–bridge–dance break; parts written for several members.
- **Register**: bright, slogan-like hooks. **Repetition**: very high; a one- or two-word hook
  ("killing part").
- **Themes**: confidence, love, youth, self-belief. **Show/tell**: tells.

### Jazz
- **Rhyme**: crafted AABB/ABAB; internal and multisyllabic rhymes; wit. **Form**: 32-bar AABA (also
  ABAC, 12-bar blues); new lyrics over each A.
- **Register**: urbane and witty — the most sophisticated in popular song. **Repetition**: structured
  by the form; the title as the first or last line of each A.
- **Themes**: love, heartbreak, nostalgia, celebration — timeless. **Valence**: positive to
  bittersweet, "sorrow without becoming beleaguered".

### Classical / art song / opera
- **Rhyme and form**: from the text's literary tradition; recitative to move the plot, aria to feel;
  strophic or through-composed Lieder.
- **Register**: the highest literary register; archaic words allowed; word painting is central.
- **POV**: characters in dialogue and soliloquy; the lyric "I" in Lieder. **Valence**: the widest range.

### Modern country
- **Rhyme**: XAXA (lines 2 and 4); perfect and identity rhyme. **Form**: verse–chorus–verse–chorus–
  bridge–chorus; the title within about a minute; "you" early.
- **Register**: conversational, regional ("ain't", "y'all", dropped g's, backroads, long Southern
  place names). **Repetition**: high; 3–5 choruses.
- **Syllables**: about 7–9, natural speech ("would you say it that way?").
- **Hook**: write to the title — story, hook, payoff. **POV**: I/you, anthem mode.
- **Themes**: small towns, trucks, Friday nights, love, drinking, pride. **Valence**: mostly positive.
  **Show/tell**: shows.

### Outlaw / traditional country
- **Rhyme**: ABAB or ABCB ballad forms; near rhyme and narrative flow tolerated.
- **Form**: verse–verse–chorus or verse with a refrain; longer songs welcome; story over chorus.
- **Register**: plain and poetic at once (the Kristofferson/Van Zandt standard).
- **Repetition**: low; storytelling. **Syllables**: about 7–10; keep lines tight by cutting articles,
  prepositions and weak verbs rather than letting them sprawl; chorus lines 2 and 4 a syllable or two
  shorter than 1 and 3 give the singer room to breathe.
- **Hook**: a refrain or a title line, often closing each verse. **POV**: first-person confession and
  third-person story alike; the narrator a flawed outsider.
- **Themes**: drinking as coping, heartbreak, defiance, redemption, work, the road. **Valence**: darker,
  honest. **Show/tell**: shows ("dust on my brim, rust on my badge").

### Americana / indie country
- **Rhyme and form**: the most varied — folk forms, refrain-anchor lines, unrhymed passages,
  through-composed story songs.
- **Register**: the richest of country — dense imagery, layered meaning, regional specificity
  (Appalachian words, named places). **Repetition**: low; a refrain-anchor line instead of a big chorus.
- **POV**: any; character-driven third person is common. **Themes**: class, justice, place, memory —
  "weathered postcards from specific places". **Valence**: nuanced, bittersweet. **Show/tell**: shows.

## 5. Hooks

Choose the hook type for the genre and the theme; combining two is allowed ("click-clack, keep it
rolling").

- **Title repetition** — the title, repeated in the chorus. Default for pop, modern country,
  commercial hip-hop.
- **Onomatopoeic** — a sound word that is rhythm and meaning at once ("click-clack" for wheels).
  For strong physical settings and cinematic stories.
- **Character as hook** — a vivid name that carries the story ("Cactus Jack"). It must pass the bar
  test: shouted across a bar, it still sounds right.
- **Mantra** — 2–5 words repeated with rising intensity. Americana, folk, gospel, anthemic rock.
- **Phonetic** — the sound pattern is the memorable part. Pop, EDM, K-pop.
- **Contrast** — a phrase that holds two opposites ("beautiful disaster"). Indie, singer-songwriter.
- **Question** — an open question that lingers. Pop, R&B, hip-hop.

A strong physical setting favours onomatopoeic or mantra hooks over plain title repetition.

## 6. Output

1. **The lyric file is the song text only**: section markers (`[Verse 1]`, `[Pre-Chorus]`, `[Chorus]`,
   `[Bridge]`, `[Outro]`) and the lines, with a blank line between sections. No title, artist, genre,
   style or any other header in it.
2. A repeated section is written out again or marked `[Chorus]` again, as the vocal tool needs —
   synthetic vocalists sing what is written, so write the repeats out unless told otherwise.
3. The genre and subgenre chosen, any assumption (an unlisted genre, a fusion, a resolved tension),
   the hook type and any departure from the genre's defaults go into the step's summary, never into
   the lyric file.
4. Annotations (why a scheme, why a form) only when asked, and apart from the lyric file.
5. When a melody, tempo or key is given, say in the summary how the lines fit it.
