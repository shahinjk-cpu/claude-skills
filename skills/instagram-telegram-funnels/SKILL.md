---
name: funnel-links
description: >-
  Every link a funnel needs: short links on your own redirect domain (e.g. Shlink), ChatPlace bot
  ref links per source, channel invite links per word, lesson pages and mirrors, UTM convention,
  verification. Use for «ссылка», «слаг», «короткая ссылка», «инвайт», «реф-ссылка», «зеркало»,
  «переставь ссылку», «ссылки для теста», «ссылки регистрации на эфир».
---

# Funnel links

## 0. Event deliverable = per-source registration links

For any event (YouTube stream, closed webinar, product launch) produce **a set of registration links,
one per source**, all leading into your bot (`https://t.me/your_bot?start=<event>_<source>` = ChatPlace
ref link -> event funnel), each wrapped in a short link `go.example.com/<event>-<source>`:

| Source | Slug pattern |
|---|---|
| Post in your Telegram channel | `<event>-channel` |
| Mailing in another bot / community | `<event>-community` |
| Email mailing | `<event>-email` |
| Instagram account | `t-<word>` (plus code word in comments/DM) |

Steps: ref links in ChatPlace (`ref_links_create`, own utm per source) -> short-link slugs -> check every
slug (302 -> bot) -> open the bot branch and confirm date/time in the text -> hand the list to whoever
sends the mailings. Keep the list in the event brief.

## 1. YouTube stream/video links in Telegram mailings – triple raw link + button

In a Telegram mailing or bot message that sends people to a YouTube stream or video:
- put the plain YouTube link in the text **three times in a row**, one per line, under «Смотреть:»;
- **plus an inline button «Смотреть эфир»** with the same raw youtube.com link – people use both;
- **no short-link wrapper, no UTM** – a raw youtube.com link opens the YouTube app straight away;
- this overrides «all links via the short domain» for YouTube links in Telegram mailings only.

```
Начинаем! Прямой эфир на YouTube: <тема>.

Смотреть:
https://youtube.com/live/<id>
https://youtube.com/live/<id>
https://youtube.com/live/<id>
```
ChatPlace mailing: write this text into the isFirstMessage block (otherwise the English placeholder goes
out). ChatPlace has no switch for Telegram link preview – a banner image in the message removes the
YouTube preview card.

## 2. Short links – your own redirect domain

All links in published content and DM buttons go through `go.example.com/<slug>` (no bare t.me, no long
UTM). Any shortener with an API works; example with Shlink (REST `/rest/v3`, headers `X-Api-Key` +
`User-Agent`; key in env `SHLINK_API_KEY`, never print it):

```bash
# create
curl -sS -X POST "$SHLINK_BASE_URL/rest/v3/short-urls" \
  -H "X-Api-Key: $SHLINK_API_KEY" -H "User-Agent: funnel-links" -H "Content-Type: application/json" \
  -d '{"longUrl":"https://t.me/your_bot?start=<word>_ig","customSlug":"t-<word>","findIfExists":true}'
# repoint
curl -sS -X PATCH "$SHLINK_BASE_URL/rest/v3/short-urls/t-<word>" \
  -H "X-Api-Key: $SHLINK_API_KEY" -H "User-Agent: funnel-links" -H "Content-Type: application/json" \
  -d '{"longUrl":"<new target>"}'
# check: expect 302 + location
curl -sS -o /dev/null -w '%{http_code} %{redirect_url}\n' "https://go.example.com/t-<word>"
```

Naming: `t-<word>` (Instagram DM button), `lesson-<name>`, `lesson-<name>-eu` (mirror), `cases-<word>`,
`yt-<name>`. Slugs `[a-z0-9-]`. Do not take existing slugs; look them up first. Back up the targets
before any bulk repoint.
zsh gotcha: `set -- $p` does not word-split – use `${p%% *}` / `${p##* }` or a function.

## 3. Bot ref links – ChatPlace

`ref_links_create {name, automationId, status: active, keepPriority: false, slug, utm}` with the key of
the Telegram bot's workspace. Link = `https://t.me/your_bot?start=<slug>`. Convention: `<word>_<source>`
(e.g. `<word>_ig`, utm `ig-main`). The short-link `t-<word>` slug points here.
Telegram limit: the start parameter is ≤ 64 chars, `[A-Za-z0-9_-]` only, no Cyrillic.

## 4. Channel invite per word

One invite link per code word gives per-word subscription attribution: the channel join carries the invite
name. Create invites through the Bot API `createChatInviteLink` (name = source, generous `member_limit`)
from a bot that is the channel admin, and store a `source -> invite` map. Invites made by hand by other
admins show up masked to a tracking bot and cannot be attributed.

## 5. Material pages

- Lesson page + EU mirror on a different host (some networks block one of them). The mirror is only the
  second «Зеркало» button, never the primary link; give it `noindex` + canonical to the main page.
- In the bot link to `lesson-<name>` / `lesson-<name>-eu` with
  `utm_source=telegram&utm_medium=bot&utm_campaign=<word>` – each word its own `utm_campaign`.

## 6. UTM convention

`utm_source` = platform (instagram / telegram), `utm_medium` = place (dm / bot / bio / channel),
`utm_campaign` = word or product, `utm_content` = post or occasion.

## 7. Test links

Give `https://go.example.com/t-<word>` – it opens the bot exactly like the DM button.
To see the «не подписан» branch a non-subscribed account is needed.
