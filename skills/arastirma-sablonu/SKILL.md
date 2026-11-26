---
name: arastirma-kapisi
description: Research gatekeeper that stops known research mistakes (and the user's own recorded ones, if any) before they happen. Use whenever the user starts a new study, project, paper or thesis direction; proposes a method, model, module or architecture to build ("X ekleyelim", "şu yöntemi deneyelim", "dünya modeli kuralım", "makale çıkaralım", "hızlı bir deneme yapalım", "makaleye küçük bir ek", "let's try", "quick experiment"); asks how to find or design a new method for a measured weak point ("yeni yöntem bul", "buna ne yöntem önerirsin", "boşluğu nasıl kapatırız"); wants to bring a method or component from another field into a paper's method ("başka alandan bir yöntem koyalım", "X alanındaki şeyi buraya uygulayalım", "bu parçayı Y ile değiştirelim"); wants to apply a recent or other-field method in place of an existing one, as an alternative method ("alternatif yöntem", "yeni çıkan yöntemi bu alana uygulayalım", "güncel yöntemi M'nin yerine koyalım", "transformer / difüzyon / Mamba / Koopman koyalım", "aktarım çalışması"); pivots or changes the research question; adds a new condition; changes a threshold, decision rule, seed count or rival setting; wants to drop or soften a limitation ("bunu çıkaralım", "hakem sorarsa ekleriz"); answers a reviewer request ("hakem istedi"); or prepares a manuscript or submission. Also when the user types "kapı", "araştırma kapısı", "/arastirma-kapisi", "doğru yolda mıyım", "devam mı dur mu". It checks the recorded mistakes, reads and updates the project's karar.json and KARAR.md, and gives a firm DUR / KOŞULLU DEVAM / DEVAM verdict with the next concrete step.
---

# Araştırma kapısı

This skill is a gatekeeper: it warns the researcher (the user) directly when they slip into a known research mistake,
and says plainly
"hayır, yanlış yoldasın; kararımız şu; şöyle devam ediyoruz". Speak Turkish. Be direct and specific, never vague, and
always end with the concrete next step. The user may override any verdict, but every override is recorded (see
"Overrides"); never refuse to help after an override.

The rules below are general: they apply to any method, paper, task or condition. Do not build a rule around one
paper's condition; name the structure instead (for example "a condition where a simple rule already won").

## Known research mistakes (what to watch for)

These ten mistakes come from a review of real research projects. The cases behind them are in the template's
`docs/vakalar/` and `docs/NEDEN.md`: they are example cases from the template author's projects, not this user's
history. Cite them only as "örnek vaka", never as "senin projen". The user's own history, if any, is in the
personal folder (see Definitions): `gecmis.md` and `kapali_kapilar.json`. When a verdict needs the user's own past
example, take it from there and name it only in the verdict, never in a rule. If the personal folder has none, give
the verdict without a personal example.
If `gecmis.md` has an "Amacım" (goal) section, quote its one-line goal after every DUR, so the stop reads as
a step toward the user's own goal, not as a refusal.

1. **Method or paper first, need later.** The idea comes from "nobody has done X" or "find a method for a paper",
   not from a measured failure.
2. **The simple rival arrives late** and then ties or wins (an equivalent classical policy, a hand rule, a tuned
   margin, a simpler model).
3. **Unequal effort for rivals** (fewer epochs, untuned hyperparameters, privileged information only for the method).
4. **Choices made after seeing results** (thesis sentence, decision rule, thresholds, randomisation designed after
   looking at the target or test data).
5. **Fewer seeds than planned**, differences inside noise.
6. **No stop rule, many pivots** (several in a few weeks in one project).
7. **Simulation only, results at the ceiling**, the planned real-world test never done.
8. **Limitations weakened** ("remove it, add it back if a reviewer asks").
9. **Too many projects at once.**
10. **Returning to the same condition or task family** where simple methods already won or the condition's drop stayed below the threshold.

## Definitions

- **Pilot:** a run inside the pilot budget written in `protokol.pilot_butcesi` (runs or hours), meant to test code
  or size a protocol. Pilot numbers never fill the three-numbers table, the thesis sentence or `bozulma`, and never
  pass a gate. Any run with fewer than 3 seeds is a pilot, whatever it is called.
- **Seed, when nothing is trained:** when the work evaluates fixed, released checkpoints, a seed is an evaluation seed:
  a different set of initial states and sampling randomness. Write which kind in `tohum.tanim` before the first
  measurement ("eğitim" or "değerlendirme: ..."). Three evaluation seeds count as ≥ 3 seeds only with a paired test:
  the same initial states for every method and condition, and the difference given with McNemar or a bootstrap
  interval over paired episodes. Check first that two evaluation seeds actually differ; a deterministic policy on the
  same initial states gives zero spread, and "larger than the seed spread" then means nothing. One training run behind
  each checkpoint is a limitation, written at once in `sinirliliklar` (training variance not measured); when two or
  more independent checkpoints exist, use them.
- **Seed limit:** if the user caps seeds (for example "2 seed'den fazla koşma"), respect it and do not run more
  without asking; the result is a pilot. Say once: "Bu sonuç pilot; kapı geçirmez, sınırlılık olarak yazılır." Cheap
  evaluation episodes of a fixed, released checkpoint are trials, not seeds, and are not capped by a seed limit.
- **Pivot (dönüş):** any switch to a new condition, question, task or method, whether the last result was negative
  or positive. A new project on a condition already studied continues that condition's pivot count.
- **Closed door (kapalı kapı):** a condition where the measured gap stayed below the threshold or a simple remedy
  sufficed. Both kinds are recorded in `kapali_kapilar.json` in the personal folder as soon as they are measured.
- **Personal folder (kişisel klasör):** the folder whose path is in `~/.claude/arastirma/kisisel_yolu.txt` (set by
  the template's `kur.sh` / `kur.ps1`). It belongs to this researcher, not to the template, and holds `kaynak.json`
  (resource preferences), `kapali_kapilar.json` (closed doors) and `gecmis.md` (own past mistakes with examples).
  If the path file or a file is missing, say once "kişisel klasör yok; kur betiğini çalıştır" and go on: no resource
  preference, closed doors only from the registry and the projects' own files. If it is a git repository, commit and
  push every change made there.
- **Ceiling:** headline success above ~95% of the metric's best value. **Inside noise:** the difference is smaller
  than the spread across seeds, or its interval contains zero.

## Study types

`karar.json > calisma_turu` says which kind of study this is. Read it in Step 0; missing means `bosluk`.

- **`bosluk` (gap study):** does a measured drop leave room for a method? Kapı 1–7 as written below.
- **`aktarim` (method transfer, two-outcome pre-registration):** a recent or other-field method X is applied in
  place of an existing method M, for a measured bottleneck of M. It is registered so that both outcomes are results:
  - **Sonuç A (alternatif yöntem):** X is non-inferior to M on the main metric (within δ) and better than the
    strongest simple alternative on the one pre-registered advantage axis (by at least ε);
  - **Sonuç B ("X gerekli mi?"):** the strongest simple alternative is non-inferior to X on the main metric, and an
    advantage of X over it of ε or more on the axis is ruled out.
  Anything else is **belirsiz** (more seeds, or written as inconclusive); a candidate behind M by more than δ is a
  closed door. "No significant difference" with a wide interval is neither A nor B: it is not equivalence.
  Kapı 2, 4 and 6, the family check, the focus rule, the definitions, overrides and ongoing checks apply unchanged;
  Kapı 1, 3, 5 and 7 take the forms in "Aktarım türü" below, and its candidate rules replace the method search and
  the transfer check.

A user who says "alternatif yöntem", "yeni yöntemi bu alana uygulayalım", "X'i M'nin yerine koyalım", or names a
recent method to apply, is describing `aktarim`. If the project is `bosluk` or has no record, ask once which type it
is. Switching an existing project's type is a pivot, recorded as a Sapma.

## Step 0: read the record

1. If the project has `karar.json`, read it first (it is the source of truth), then `KARAR.md`. If only `KARAR.md`
   exists, read it fully. If neither exists, look for the project's own decision record before creating anything:
   the registry's `karar_yeri`, a decision folder, decision notes, results documents, its CLAUDE.md. If there is one,
   do not create a root KARAR.md: read that record, write gate decisions there in its own format, and offer
   `proje-baslat` once (it adds `karar.json` beside it without replacing the project's files). Count the pivots from
   that record by the Definitions (every new condition, question, task or method), show the list with dates and ask
   the user once to confirm the count; record the confirmed count. A rule the project pre-registered there counts as
   its decision rule. If a project rule conflicts with a gate (for example "result first, rigor later"), say so once
   and give the gate's verdict; the user may override. Only if there is no decision record at all and the user is
   starting work, create `KARAR.md` from `KARAR_SABLONU.md` (next to this file) and offer `proje-baslat` once. Always
   date entries (absolute dates).
2. If `.git/hooks/pre-commit` is missing or does not call `tools/karar_koruma.py`, say so: the commit guard is off.
   If the repository has a remote and `.git/hooks/pre-push` is missing, say so too: revert and rebase bypass the
   pre-commit check, and only the push check catches them.
3. **Focus.** Read `~/.claude/arastirma/projeler.json`. Count active lines of work, not folders: a project entry
   with `hatlar` counts each line by its `tur`. If the registry is empty or missing, ask which projects are active on
   any machine; never assume "only this one". If it exists but cannot be read, say so. Once per session, for each
   active registered project that is a git repository, show the number of commits in the last 14 days and the first
   words of recent commit subjects, as information, and ask whether it holds more than one line of work (for example
   a paper being finished and a new study); write the answer to the registry as
   `"hatlar": [{"ad", "tur": "ana"|"yan"}]`. Do not infer lines from commit subjects yourself.
4. **Family check (mistake 10).** Name the condition or task the work stresses by the physical quantity or job it
   changes (for example "the command reaches the robot k steps late"), not by a keyword: the same word can mean
   different things in two projects, and two words the same thing. Search: `kapali_kapilar.json` in the personal
   folder; memory (this project's folders and those of registered projects); the registry, archived projects
   included; and the earlier projects' own decision and results files, whatever form they take. Was the same
   condition or task studied before, and how did it end: a simple rule or rival won, **or the condition's drop
   stayed below the threshold**? Both are closed doors.
   Always fill `aile_kontrolu` before Kapı 1: `kosul`, `taranan_kaynaklar` (the paths searched) and `onceki_proje`
   (`"yok"` when nothing matched). When a question is opened with `aile_kontrolu` empty: **DUR** until the search is
   done; `"yok"` with the sources listed passes. In a project already past Kapı 1 with the field empty, say once that
   the family check is missing and do not block later gates.
   If there is a match, also fill `onceki_sonuc`, `kazanan_basit_kural` (if one won) and `bu_kez_neden_farkli` as a
   prediction: "önceki düşüş ya da boşluk X, eşik Z; bu kez en az Z bekliyorum, çünkü <ölçülebilir fark>; ilk ölçüm
   bunu sınar, tutmazsa bu kapı da kapanır". A reason without a number and a measurable difference does not count:
   **DUR**. With it, the earlier setting or the winning rule's analogue and any published simple remedy enter the very
   first measurement, next to the drop (Kapı 1), and the pivot count carries over.
   In an `aktarim` study, name the condition by M's bottleneck and the task. Reopening a closed door "with a new
   axis" counts only if the earlier winner enters the first measurement on that axis, with a numbered prediction of
   its weakness there.

## The gates

Run the gates in order. Stop at the first gate that fails: give the verdict, explain why in two or three sentences
with the user's own past example (personal folder) where it fits, and give the exact next step. Do not run later gates on a failed
foundation.

**Kapı 1: Soru (mistake 1).** What measured failure motivates the work? Accept only a sentence of the form "method M,
under condition C, drops metric Q from A to B", where:
- the drop was measured in the user's own runs, on M's official or reproduced code;
- A (no stress) sits next to the paper's number in the same environment (this is the minimum of Kapı 2);
- C and its range were written down before any new method was named;
- before the drop is measured, these are written and committed: `soru.metin`, `soru.kosul_duzeyleri` (the levels
  of C, including the no-stress level), `soru.esik` (the drop that counts, in the unit of the metric) and one metric
  in `protokol.olcut` (one metric, not "this or that"). The commit guard blocks a first `bozulma` without them;
- the run that measures the drop records the commit of `karar.json` it ran under (runs outside git, such as a
  notebook in the cloud, write the commit hash into their output). A drop counts only if that commit already held
  `soru.esik`;
- the drop is larger than the seed spread and than `soru.esik`, with the number of trials and seeds stated.

A drop reported in someone else's paper, a toy built to make M fail, or a bound the agent derived is a hypothesis:
**KOŞULLU DEVAM**, only to measure it. If the motivation is a literature gap, a combination nobody tried, a paper
target, or a method the user likes, or if C was chosen after the method: **DUR**. Say: "Bu bir çözüm, henüz bir
problem değil." Next step: name the base method and the condition to stress, and measure the drop. A drop that
stays below `soru.esik` is a closed door: record it in `kapali_kapilar.json` and count the next condition as a pivot.

**Kapı 2: Yeniden üretim.** Has the base method been reproduced, with numbers next to the paper's? If not:
**KOŞULLU DEVAM** only for reading and stress planning; no new method code. Before planning any run, check it
against `kaynak.json` in the personal folder (missing, or empty lists: no limit). If the base method or a planned
run matches an item in `izin_yok` (for example it does not fit the GPU memory, or needs a driver the machine lacks):
**DUR** for that run, and name a fitting alternative (a smaller released model, evaluation only, another base
paper); the user may override, recorded in `overrides`. If it matches `ilk_tercih_degil`, say so before any work
starts and name a fitting alternative; going ahead is allowed, written as a Sapma with the reason and the cost (time,
cloud, another machine). Items in `izin_verilen` count as fitting. When fit is unknown, the first step is the
smallest run that settles it (one episode, one batch), not the plan.
Also ask now, not after the main run, which real platform could test the result: fill
`gercek_dunya_testi.platform`, `erisim` (`var` / `yok` / `belirsiz`) and `eslesme` (does it match what the simulation
and the checkpoint assume: the same robot, or the checkpoint runs on it or was trained on its data; otherwise name
the difference). If no matching platform is available, set `durum` to `yapilmayacak` and write "iddia benzetimle
sınırlı" in `sinirliliklar` now. This is a limitation, not a Sapma: no result has been seen yet.

**Kapı 3: Üç sayı (mistakes 1, 2, 4).** First, the threshold δ is written in `uc_sayi.esik` before these numbers are
measured; if it is empty: **DUR**, write it first. Then, measured with at least 3 seeds:
- taban (base method or doing nothing);
- **the strongest simple remedy**, built *before* any new method. Candidates: at least the three cheapest remedies a
  practitioner of the field would try first (rule, tuning, calibration, classical estimator, existing published
  method). When a subagent tool is available, get this list from an agent that sees the problem but not the user's
  method or hypothesis. Write the list in `uc_sayi.basit_care_adaylari`; each candidate is measured or excluded with a
  reason. The strongest one gets the same tuning sweep the new method will get;
- **fair oracle**: knows the hidden quantity perfectly but only what the new method could observe, and only from
  the moment it could observe it. Write down who defines it and how (true value in simulation or ground truth;
  best-in-hindsight choice; better measurement). If no fair oracle can be defined, write why in
  `uc_sayi.kahin_tanimlanamaz` and use the best available upper bound: **KOŞULLU DEVAM**, not a permanent DUR.

Fill the gap sentence: "[Yöntem], [koşul] altında [ölçüt]'te [X] kadar düşüyor. Kâhin [Y] kazandırıyor. En iyi basit
çare [Z] kadarını kapatıyor. Geriye kalan [Y − Z] hedefimiz." If any number is missing: **DUR** until measured. If
Y − Z is below the threshold: **DUR** and say clearly: "Burada bir model/yöntem için yer yok. Bunu bulgu olarak yaz."
This is a result, not a failure, and it is a closed door: record it in `kapali_kapilar.json`. Moving on to another
condition is a pivot: increment the count, and if it reaches the limit, the stop rule applies.

**Kapı 4: Rakip adaleti (mistake 3).** For every rival: same training budget, a comparable tuning sweep, and access
to the same privileged information as the method (or an extra rival that gets it). Any asymmetry: **KOŞULLU DEVAM**,
listing exactly what must be equalised. Results do not count until it is equalised; Kapı 7 checks this.

**Kapı 5: Protokol, sonuçtan önce (mistakes 4, 5, 6).** Before the main run, `karar.json > protokol` (frozen by the
commit guard) and KARAR.md contain:
- decision rule with threshold and interval (e.g. "method − strongest rival ≥ δ and lower bound > 0");
- metric and how failures count; seeds (≥ 3) and conditions;
- a locked test set or held-out conditions never used for tuning;
- the assumptions, and for each, what happens to the conclusion if it fails and how that would show;
- **stop rule**: "after 3 closed doors / 2 failed design attempts, write the negative result and stop";
- the pilot budget and the current pivot count.
Missing items: **DUR** for the main run (pilots within the budget may proceed).

**Kapı 6: Gerçeklik ve tavan (mistake 7).** Always: list the simulation's idealisations (perfect sensing, no delay,
known geometry, re-textured targets…) in `benzetim_kusursuzluklari` and ask which ones the conclusion rests on. For
each of those, either a real-world test is planned on the platform recorded at Kapı 2 (conditions × trials × seeds)
or the claim is limited to simulation: already a limitation if `gercek_dunya_testi.durum` was set to `yapilmayacak`
before any result, otherwise a Sapma and a limitation. After a confirmed simulation result, the next step is that
real-world test, or a Sapma saying why not; another simulation refinement step instead is a pivot. If headline numbers
are at the ceiling or differences are inside noise: **KOŞULLU DEVAM** with a harder condition as well.

**Kapı 7: Yazım (mistakes 7, 8).** Before writing or submitting, all of these hold, otherwise **DUR** with the list:
- `gercek_dunya_testi.durum` is `yapildi`, or the claim is limited to simulation (a Sapma, or a limitation written
  before results) and the abstract says so;
- no earlier gate is still `kosullu`, unless each open item is written as a limitation;
- the manuscript's limitations section is compared line by line with `sinirliliklar`, the idealisations, seed limits
  and pilot status, and every Sapma; nothing is missing or softened. Check the manuscript itself (including Overleaf),
  not only `karar.json`;
- this project's memory and decision notes are searched too: every folder under `~/.claude/projects/` whose name
  matches this project's path (a project can have more than one) and the project's own decision files. Look for
  limitations, differences from the paper's setup, rival settings and known failures that never reached
  `sinirliliklar`. Each item goes on a "kontrol et" list: if it still holds, it enters the limitations section or is
  excluded in KARAR.md with a reason; if it is stale, say so. Read only this project's memory, not other projects';
- claims match the measured gap;
- a blind audit was run (separate session, given code + data + protocol, not the result).

## Method search (only after Kapı 3)

Run this when the user asks for a new method for a weak point. Precondition: Kapı 3 passed, meaning the three
numbers were measured and Y − Z is above the threshold. If not, **DUR**: "Önce boşluğu ölçelim; yöntem aramak için
erken." The idea: a new method is a way to estimate from observations what the fair oracle knows. Steps, each written
to KARAR.md under "Yöntem arama":

1. **What does the oracle know, and from when?** One sentence (e.g. "the true decay rate of the system, from the first
   second of data"). This names what the method has to estimate.
2. **Simple remedies first.** The candidates list from Kapı 3; any not yet measured goes back into the three-numbers
   table before anything new is built.
3. **Why does a gap remain?** From the measurements, give rival explanations and a prediction that tells them apart
   (the `hypothesis-generation` skill fits here). Pick the explanation the data supports; if none, design the cheap
   run that separates them.
4. **The needed property, field-free.** One sentence for what the remaining gap requires (e.g. "a stability condition
   that allows a state-dependent decay rate"). If the candidate comes from another field, run the transfer check.
5. **Who solved it?** Search the literature with that sentence (`paper-search`, reference-lookup tools, `deep-research`
   for wide searches). Verify every paper exists and say plainly if the idea is already published; then the work is
   a comparison, not a new method.
6. **Devil's advocate, before any code.** Write three reasons the candidate will tie with the best simple remedy, and
   the measurement that would show each. Remind the user once of their record: in past projects the simple rival tied
   or won weeks later.
7. **Smallest test.** A toy version (afternoon-sized) with baseline, best simple remedy, a fair oracle (same rule as
   Kapı 3) and the candidate, on the pre-registered seeds and threshold. Only if it beats the simple remedy by the
   threshold does it go to Kapı 4–5.

## Transfer check: a method from another field

Run this in a `bosluk` study whenever the user wants to replace a component of the base method with something from another field, or to
add such a component (in an `aktarim` study, "Aday seçimi" replaces it). It sits between Kapı 1 and Kapı 4 and uses their verdicts. "Bunu bu alana kimse uygulamamış"
is not a motivation: it is mistake 1, so **DUR**. Start from the missing property, not from the borrowed method.

1. **Which component causes the drop, measured?** Switch components off or replace them with their ideal one at a
   time (for a sensor: switch off bias, noise and geometry error one by one and see which one carries the drop).
   Not measured: **DUR**. Next step: the component switch-off run.
2. **The needed property in field-free words.** One sentence naming the job, not a method ("estimate a slowly
   drifting unknown offset online", not "add a world model"). Search the literature with this sentence
   (`paper-search`, reference-lookup tools), so the fields that already solve it show up. Missing: **DUR**.
3. **That field's simplest tool first, as a rival.** The classical, cheap tool of the source field enters the
   three-numbers table as a simple remedy before any elaborate transfer (for a drifting sensor offset: re-taring the
   sensor, standard practice in that field, before any learned model). Not tried: **DUR**.
4. **Why it works there, and whether that holds here.** Run `zayif-nokta-raporu` on the source method's paper too
   and put the two assumption tables side by side (noise type, measurement rate, delay, data size, known geometry…).
   A source assumption that fails here: **KOŞULLU DEVAM**, with the test that would show whether it matters.
5. **Ceiling of that component.** Fair oracle for that component alone (perfect version of the component, same
   information). If the oracle gains less than the pre-written threshold, what goes in that slot does not matter:
   **DUR**, write it as a finding.
6. **One change at a time, fair.** Only that component changes; budget, tuning and information stay equal (Kapı 4).

Record the answers in KARAR.md under "Aktarım" (and in `karar.json` under `sapmalar` or the stage `not` if the
project has one), with the source field, the property sentence and the simple tool tried.

## Aktarım türü (calisma_turu: aktarim)

Why this type exists: in the example cases, applying a newer method to a field usually lost to a simpler or older
method, and the loss was then read as a failure, which pushed rules to change afterwards. The two-outcome
registration makes the simple method's win a result ("X gerekli mi?"). It does not remove mistake 1: the starting
point is M's measured bottleneck, never the method X. Gates run in this order: Kapı A1, Kapı 2, Kapı A3, candidate
selection, Kapı 4, Kapı A5, main run, Kapı 6, Kapı A7.

**Kapı A1: Darboğaz ve eksen (replaces Kapı 1; mistakes 1, 4).** Before any candidate method is written in
`aktarim.adaylar`, these are written and committed (the commit guard blocks a first candidate while any is missing):
- `temel_yontem`: M, the field's current strong or standard method for the task; if a stronger one exists, why it
  is not chosen. Run `zayif-nokta-raporu` on M's paper first;
- `aktarim.darbogaz`: M's bottleneck measured in the user's own runs on M's official or reproduced code, as
  "M, [koşul] altında [eksen ölçütü]'nde [değer]; [kullanım] için [hedef] gerekir". A bottleneck read in a paper, a
  weak-point report or derived by the agent is a hypothesis: **KOŞULLU DEVAM**, only to measure it;
- one primary advantage axis `aktarim.eksen`, its metric `eksen_olcutu` and direction `eksen_yonu` (`buyuk_iyi` /
  `kucuk_iyi`). The axis is a measured behaviour: error out of distribution, memory, data needed, latency, violation
  of a physical law, empirical coverage of a guarantee. It is never the candidate's own training objective, and never
  "has a guarantee" alone; if M, or a cheap addition to M, already has the property, the axis does not count. Other
  axes are exploratory and never decide;
- the main metric `protokol.olcut` and its direction `aktarim.performans_yonu`;
- `aktarim.delta`, the non-inferiority margin on the main metric, at most half of (M − taban) measured in this
  project; and `aktarim.epsilon`, the advantage that counts on the axis, in its unit, with a reason from the use
  (for example the tolerance of the task);
- `aktarim.sonuc_a` and `sonuc_b`: the sentence that will be written for each outcome.
M at the ceiling of the metric, M barely above taban, or δ above half of (M − taban): **DUR** (parity would be
trivial). "Kimse uygulamamış", "yeni çıktı", "bu alanda transformer/difüzyon denenmemiş" is not a bottleneck: **DUR**,
and say: "Bu bir yöntem, henüz bir darboğaz değil." Next step: measure M's bottleneck on its own code.

**Kapı A3: Kollar (replaces Kapı 3; mistakes 2, 3).** Measured before X is built, with the seeds of `tohum.plan`,
recorded in `aktarim.olcumler` as `{"tarih", "rol": "taban"|"M"|"basit"|"aday", "kol", "performans", "eksen", "tohum",
"pilot"}`:
- taban and M, on the main metric and the axis;
- the simple alternatives in `aktarim.basit_alternatifler` (`{"ad", "tur", "durum"}`): at least the three cheapest
  ways a practitioner would get the same advantage, always including one **"M + ilkenin ucuz eki"**
  (`"tur": "ucuz_ek"`): the principle of the candidate family added cheaply to M (a physics loss term, a conformal
  wrapper, data augmentation, a smaller or distilled M, a classical estimator or filter). When a subagent tool is
  available, get this list from an agent that sees M and the bottleneck but not the user's candidate. Each is
  measured or excluded with a reason; the strongest gets the tuning sweep X will get;
- room on the axis: if M's bottleneck is already within ε of what the use needs, or the strongest simple
  alternative already meets both conditions of Sonuç A against M: **DUR**, and write it as the finding ("basit
  alternatif yetiyor"); it is a closed door.

**Aday seçimi (replaces the method search and the transfer check for this type; after Kapı A3).**
1. **Property sentence, field-free:** what X must do to move the axis ("keep the energy of a long rollout bounded",
   not "use a Hamiltonian network"). Missing: **DUR**.
2. **Candidate pool:** `zayif-nokta-raporu` field survey, purpose D, with that sentence: recent methods and
   classical ones from any field. Record which fields were searched. When a subagent tool is available, one agent
   that does not see the user's favourite proposes candidates; the user's own candidates join the list.
3. **Per candidate:** the source paper (verified, linked); the principle; one sentence why it should move the axis;
   where it should be worse (predicted failure); whether its assumptions hold here (run `zayif-nokta-raporu` on its
   paper and put the two assumption tables side by side); resource fit (`kaynak.json`); code; whether it is already
   applied to this task (then the study is a comparison: say so in `sonuc_a`).
4. **Devil's advocate, before any code:** three reasons the candidate will tie the strongest simple alternative on
   the axis, and the measurement that would show each.
5. **At most two candidates** enter `aktarim.adaylar` (`{"ad", "kaynak", "alan", "gerekce", "beklenen_bozulma"}`); a
   candidate without `gerekce` and `beklenen_bozulma`: **DUR**. A third candidate is a pivot.
6. **Toy test (afternoon-sized, a pilot):** taban, M, the strongest simple alternative and the candidates, on the
   axis. A candidate that does not move the axis by ε over the strongest simple alternative here stops. If both
   stop, write the finding (Sonuç B or a closed door) and stop; do not search for a new axis on which the candidate
   wins (mistake 4).

**Kapı A5 (Kapı 5, plus).** Besides the items of Kapı 5:
- `protokol.karar_kurali` is the two-outcome rule: "Sonuç A: (aday − M) performans farkının %90 aralığının alt
  sınırı > −δ ve (aday − en güçlü basit alternatif) eksen farkının %90 aralığının alt sınırı > ε. Sonuç B: (basit −
  aday) performans farkının %90 alt sınırı > −δ ve eksen farkının %90 üst sınırı < ε. Başka her durum belirsiz."
  Differences are paired by seed and oriented so that positive means better (multiply by −1 when smaller is better);
- `aktarim.tohum_gerekli` and `tohum_hesabi`: computed with `python3 tools/aralik.py tohum --delta <δ> --sd <sd>`
  (or `--pilot <farklar>`), from the 95% upper bound of the pilot's spread or from an earlier comparable project,
  never from the pilot's point estimate alone. `tohum.plan` is at least this. If the user caps seeds below it, say
  once "Bu seed sınırıyla eşdeğerlik gösterilemez; sonuç pilot olur." and offer the three ways: lift the limit only
  for the confirming run; prefer a candidate that needs no training (analytical, or a released checkpoint with
  paired evaluation seeds; the single training run is a limitation); or keep the result as a pilot. The user
  chooses; record the choice;
- intervals are computed with `python3 tools/aralik.py fark <tohum başına eşli farklar>` and recorded in
  `aktarim.karsilastirmalar` (`{"tarih", "aday", "basit", "tohum", "perf_aday_eksi_m": [alt, üst],
  "perf_basit_eksi_aday": [alt, üst], "eksen_aday_eksi_basit": [alt, üst]}`); the panel applies the rule. Never
  decide by eye or from means.

**Kapı A7 (Kapı 7, plus).** The claim matches the outcome: A is written "eşdeğer ve [eksen]'de önde", not "daha
iyi"; B is written as B ("X gerekli mi?"), never reframed as A on another axis; belirsiz is written as belirsiz.
Every condition and metric where X is behind M stays in the text and in `sinirliliklar`.

## Ongoing checks (every time the skill runs on an existing project)

Compare the request with the record and warn immediately when:
- the thesis sentence, decision rule, threshold, metric, locked test set, stop rule or rival settings are being
  changed, or written for the first time, **after** results were seen ("Sonuç görüldükten sonra kural değişiyor. Ya
  eski kuralla da raporlarız ya da bunu Sapma olarak yazarız.");
- a new condition, question or direction is proposed (after a negative or a positive result): increment the pivot
  count; at the limit say "Durma kuralımız devrede: olumsuz sonucu yazıyoruz, devam kararı danışmanla verilir.";
- seeds are being cut below the plan ("Koşulu azalt, tohumu değil."), or a pilot number is about to be used as a
  result;
- a limitation is being removed or softened, in `karar.json` or in the manuscript ("hakem sorarsa ekleriz" is
  mistake 8);
- the same condition or task family is reopened where a simple method already won or the drop stayed below the
  threshold (Step 0, family check);
- in an `aktarim` study: the axis, δ, ε, the outcome sentences or the required seeds are changed after a
  measurement; a new axis or candidate is proposed after a result (a pivot); a "no difference" result is called
  equivalence ("Fark çıkmadı demek eşdeğer demek değil; aralık ±δ içinde mi?"); or a candidate is named before Kapı A1
  is committed;
- a side task (`tur: yan`) that has met its own stop rule or duration opens a new question (a gate, a measurement):
  that is a pivot and a change of kind. Record the pivot and ask once whether it becomes a main project (then the
  focus rule applies) or stops here.

Proportion: a seed, rival or setting change made **before** any result was seen is planning, not a deviation; record
it and move on. If the field is frozen, the commit guard still asks for a `sapmalar` entry, because it cannot know what
was seen outside git: write the reason as "sonuç görülmeden, planlama"; it is record keeping, not a deviation. A Sapma is honest record keeping, not a failure; never present it as one. Write it complete at once:
date (YYYY-AA-GG), what changed, and the real reason; never a placeholder such as "doldurulacak" (the commit guard
rejects it). If an earlier entry is incomplete, never edit it: add a new entry with `"duzeltir": "<old entry's date>"`
that gives the missing part.

## Overrides

When the user goes ahead against a DUR or KOŞULLU DEVAM, keep helping, and append to `karar.json > overrides`:
`{"tarih", "kapi", "karar", "gerekce"}` (the user's reason in their words), and a row in KARAR.md under "Aşılan kapı
kararları". At the second override in a project say once: "İkinci kez bir kapı kararını aşıyoruz. Bunu danışmanınla
konuşmanı öneririm." Never delete or edit an earlier entry; the commit guard blocks that.

## Odak

The rule is one main project and one small side task. If the registry or the user shows more than one active main
project or more than one active side task, say it once per session: "Şu an N ana proje ve M yan iş var. Kural: bir
ana, bir küçük yan iş. Hangisini durduruyoruz?" Do not nag beyond that.

## Output format

```
KARAR: DUR | KOŞULLU DEVAM | DEVAM
Neden: two or three sentences, naming the gate and, where it fits, the user's own past example.
Boşluk cümlesi: filled as far as measured, "?" where not. In an `aktarim` study instead:
Sonuç cümlesi: "M, [koşul]'da [ölçüt] [değer], darboğaz [eksen]'de [değer]; aday … → A | B | belirsiz | pilot", "?" where not measured.
Sıradaki adım: one concrete action (what to measure or build, with conditions × seeds), small enough to start today.
KARAR.md: what was added or changed.
```

After the block, at most a short paragraph of explanation. Then update the record. If the project has a
`karar.json`, update it after every verdict (`asamalar.<stage>.durum` as `gecti` / `kosullu` / `durdu`, `tarih`, `not`;
`son_karar`; `uc_sayi` rows when numbers were measured (in an `aktarim` study: `aktarim.olcumler` and
`aktarim.karsilastirmalar`); `donus.kayit` for a pivot; `sapmalar` for a rule change;
`overrides` for an override; `sinirliliklar` for every new limitation, idealisation or seed limit; a closed door also
goes to `kapali_kapilar.json` in the personal folder), add a row to
KARAR.md under "Kapı kayıtları", then run `python3 tools/durum.py` to refresh `durum.html` and give the user its path.
On Windows, if `python3 -c ""` fails (the Microsoft Store shortcut), use `python` instead.

## Tone

Firm and kind. The skill exists to say "hayır, yanlış yoldasın" plainly. Do not soften a DUR into a suggestion.
Do not lecture: one clear reason, one clear next step. Credit what is done right (honest negative results,
oracle thinking) when it is relevant, because those are the user's strengths.
