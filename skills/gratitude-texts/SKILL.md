---
name: gratitude-texts
description: Build one Google Sheet of everyone you interacted with over the past year, from iMessage, plus email and calendar when connected, ranked by how close you are, with a short drafted message for your highest-priority people. Made for holiday check-ins (Thanksgiving by default) but works any time. Never sends anything; you reach out yourself. Mac only. Triggers - "gratitude texts", "thanksgiving texts", "who should I reach out to", "list everyone I talked to this year", "holiday check-in list", "touch base with everyone".
user-invocable: true
---

# Gratitude Texts

This skill builds a single Google Sheet of the people you interacted with over the past year, ranks them, and drafts a short personal message for the top few. You work through the Sheet and reach out yourself.

Four rules hold the whole way through:

1. **This skill never sends anything.** Don't send messages, emails or invites, and don't write or run any code that does, even if the user asks mid-run. If they want automated sending, tell them it's outside this skill.
2. **Get approval before reading anything.** Step 0 comes first, every time.
3. **The data stays local.** The scripts open the databases read-only and write only to `~/gratitude-texts/<year>/`. Message snippets pass through the model only for the few people you draft for. The finished list goes to Google Sheets in the account the user approved, and nowhere else.
4. **Never make anything up.** A personal line has to come from something actually in the messages. If nothing fits, leave it out.

Scripts are in `scripts/` next to this file. The working folder is `~/gratitude-texts/<year>/`, and it is called `DIR` below.

## Step 0: Explain, then get approval

Before running anything, send the user this rundown, adapted to which connectors are available, and wait for a clear yes:

> **What this does**
> 1. **Reads your Messages and Contacts on this Mac**, read-only, to find everyone you've had a two-way text thread with in the past year. Group chats, verification codes and businesses that never reply are left out.
> 2. **Optionally checks email and calendar** if Gmail or Google Calendar is connected: people you emailed and people you met with. (Say which accounts are connected. Each connector covers only its own account.)
> 3. **Builds one list**, ranked into high, medium and low priority by how much you talk and how recently.
> 4. **Drafts a short message for your top ~25 people only**, using a few recent messages with each of them for context. Everyone else gets a row with no draft.
> 5. **Puts it in a Google Sheet** in your Google account <name the account the Drive connector uses>, private to you, with a checkbox for each person you reach out to. That copies names, numbers and drafts into that account. (If Google Drive isn't connected, say you'll leave a local `people.csv` instead.)
>
> **What it never does:** send any message or email, change your data, or upload anything without your OK.
>
> **What it needs:** Full Disk Access for the app running Claude Code, so it can read Messages and Contacts, and a Google Drive connector for the Sheet.
>
> Settings: occasion **Thanksgiving**, lookback **1 year**, drafts for the **top 25**. Your template is `Hey {first}, happy Thanksgiving! Grateful to have you in my life. {personal}` Want to change any of these, or exclude anyone, like family or coworkers? Reply **yes** to start.

Keep the user's own template wording if they give one. Don't start Step 1 until they approve. If they decline the email or calendar part, skip it.

## Step 1: Texts

```bash
python3 scripts/find_people.py --out ~/gratitude-texts/$(date +%Y)
```

This covers the past year, everyone with at least one message each way. If it prints a Full Disk Access error, tell the user the steps it prints, once. If access is still denied after they've granted it, the app almost always needs a full quit (Cmd+Q) and reopen. Closing the window isn't enough. Don't retry in a loop.

## Step 2: Email and calendar (optional, if approved)

- **Email:** search `in:sent after:<one year ago>` in date slices of 1 to 2 months, because results cap per call and may not paginate. Write every recipient address (to, cc, bcc), one per line, to `DIR/email_sent.txt`.
- **Calendar:** list the past year's events. Save guests who aren't the user as `[{name, email, last, count}]` to `DIR/calendar.json`.

Only collect addresses, names and dates. Don't read email bodies.

## Step 3: Build the list

```bash
python3 scripts/build_list.py --dir ~/gratitude-texts/$(date +%Y) --self <the user's own email addresses>
```

This writes `people.csv` with the columns `done, priority, name, phone, email, sources, texts, last_contact, draft, notes`. Sorting is high, then medium, then low.

- **high**: the top `--high` (default 25) by texting score, which rewards two-way volume and recency
- **medium**: a real back-and-forth, a meeting, or more than one channel
- **low**: everyone else

Then skim the high and medium rows in `people.json` and fix what the score gets wrong. Write the fixes to `DIR/notes.json` as `{"<name or phone or email>": {"priority": "...", "notes": "..."}}`:

- Businesses, landlords, recruiters, deliveries: `low`, with the note `business`.
- The user's exclusions, and family by default (most people call family): `low`, with a note like `family` so the user can see why.
- Threads showing conflict, a breakup, or a request to stop contact: `low`, with the note `check first`.
- Dating, work or client threads where the tone is unclear: keep the priority, with the note `check tone`.
- Number-only rows: add the name in `notes` if the messages give it ("it's Sam from the climbing gym").

Keep every row. The point is one complete list. Notes explain the ranking rather than hiding people.

## Step 4: Drafts for high priority only

For each **high** row without a `check first` note, read that person's `recent` messages in `people.json` and fill the template:

- `{personal}`: one sentence of about 15 words at most, true and specific, in the user's own casual register with that person. Prefer the last 6 months, and treat older things as past ("hope the marathon went well").
- Leave `{personal}` out if the recent topic is sensitive: health, grief, money, divorce, job loss, legal trouble. Never repeat private details in a way that reads as surveillance. When unsure, leave it out.
- For someone texted in the last ~2 days, refer to that exchange instead of "catching up soon".
- Put a few words on where the line came from in `notes`, like "new job in Denver".

Don't draft for medium or low rows. Write the drafts to `DIR/drafts.json` as `{"<name or phone>": {"draft": "...", "notes": "..."}}`, then rerun Step 3's command to merge them in.

## Step 5: Make the Google Sheet

`people.csv` in `DIR` stays the local source of truth. The Sheet is the copy the user works from.

1. Upload `people.csv` with Drive `create_file`, using `contentMimeType: text/csv` and a title like `<Occasion> <year> - people`. Drive converts it to a Sheet. If the connector can't read files by path from `DIR`, copy the file into a scratch folder first and delete the copy afterward.
2. Format it with the Sheets `update_spreadsheet` tool:
   - freeze row 1 and the first three columns, and bold the header
   - checkboxes on `done`, and a `high / medium / low` dropdown on `priority`
   - a filter on the whole table
   - widen and wrap `draft` and `notes`
3. Read back the first and last rows to confirm everything landed.

If no Google Drive connector is available, skip this step and open `people.csv` locally (`open people.csv`).

## Step 6: Hand over

In chat, tell the user:

- the Sheet link and the account that owns it
- the total count and the high / medium / low split
- which sources were covered and which weren't, for example "Gmail: work account only"
- 5 sample drafts
- that `done` is for them to tick as they reach out, and that nothing was sent

If they want changes ("drop Alex", "shorten Priya's", "draft for the next 10"), edit `drafts.json` or `notes.json`, rebuild, and upload a fresh Sheet. Ask before trashing the old one. If they've already ticked boxes or edited the Sheet, read those edits back with `get_values` first, so a fresh upload doesn't lose their work.

## After

Suggest they keep `DIR`, since next year's run can start from it. The skill doesn't read replies or follow up on its own.
