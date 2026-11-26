# Insights (read-only reports)

```bash
python3 SKILL_DIR/scripts/insights.py --workspace <ws> due                     # today's follow-ups, interviews, check-ins
python3 SKILL_DIR/scripts/insights.py --workspace <ws> weekly                  # search health + one suggestion
python3 SKILL_DIR/scripts/insights.py --workspace <ws> employers --suggest-ats  # who keeps posting jobs the user can take
python3 SKILL_DIR/scripts/insights.py --workspace <ws> companies               # reply rate, days to reply, interview formats
python3 SKILL_DIR/scripts/insights.py --workspace <ws> skills                  # most-requested skills the user lacks; pay linked to skills
```
- **weekly:** offer it at the first session of each week; relay the suggestion and follow-ups.
- **employers:** after a week or two of scans. `--suggest-ats` finds job boards by company name; ask the user to confirm each is the right company. `--add` writes them into `filters.md` once the user agrees.
- **companies:** before a follow-up or interview, and to decide which companies to drop.
- **skills:** gaps are learning options. "Do NOT claim" skills stay gaps until the user confirms new experience. Extra terms: `filters.md` → `skills.extra`.
