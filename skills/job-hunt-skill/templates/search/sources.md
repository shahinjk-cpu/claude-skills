# Job sources

Implemented in the skill's `scripts/scan.py`. Turn on/off in `search/filters.md` → `sources`.

| Key | Board | Coverage | Notes |
|---|---|---|---|
| `remoteok` | RemoteOK API | global remote, tech | Full feed (~100). Location often "US Only" |
| `remotive` | Remotive API | global remote | Free API returns only ~15 recent jobs per request (Nov 2026). One request, cached 6 h, max 4/day (their terms); queries matched locally. Salary as free text |
| `himalayas` | Himalayas API | global remote | Per query, `locationRestrictions` list (empty = unrestricted) |
| `jobicy` | Jobicy API | global remote | Per query as tag. `jobGeo` |
| `weworkremotely` | WWR RSS | global remote | Category feeds. `region` tag |
| `workingnomads` | Working Nomads API | global remote | Small feed |
| `hn` | HN "Who is hiring" | startups, many remote | Latest monthly thread found automatically |
| `arbeitnow` | Arbeitnow API | Europe (mostly DE) | Mostly onsite. Enable for EU candidates |
| `getonbrd` | GetOnBoard API | LATAM | Never add `expand=` (returns 0) |
| `gupy` | Gupy portal | Brazil | **Off by default, not recommended:** Gupy's candidate terms forbid aggregating, copying or duplicating postings. Search Gupy by hand; many Gupy jobs also reach other sources. If you enable it anyway, it's your decision (a warning prints on every scan) |
| `perfectrole` | perfectrole.app | global | Off by default. robots.txt allows the job sitemaps and pages; their terms of use weren't found, so check them before enabling |
| `remoterocketship` | Remote Rocketship API | 100k+ company career pages | **Needs a paid API key** at `~/.config/remoterocketship/api-key`. Location only in the URL slug |

## Manual-only (login walls / anti-bot, don't scrape)
LinkedIn, Indeed, Glassdoor, Wellfound. Search them yourself with filters: role · Remote · your country/region · past week.

## Verifying a company
Use the skill's `verify_company.py` (domain age, mail, website, job board, recruiter email).

## Notes
_(add quirks, broken endpoints and yield observations here)_

## Company job boards (`ats` source)
Public JSON APIs, no key: Greenhouse, Ashby, Lever, Workable. List target companies in `filters.md` → `atsBoards`. Most companies hire locally, so the value is catching a remote opening for your region the day it's posted. Many large companies use Workday or their own site instead: check those by hand.

## Pages that block plain HTTP
If a page needs JavaScript or blocks scripts (some LinkedIn posts, some career sites), a scraping MCP such as Firecrawl can read it. Use it only as a fallback for single pages; free tiers have small credit budgets.

## Terms of use
- Never republish job data on other sites or use it to collect sign-ups. This workspace is for your personal search.
- Respect each source's rate limits. Don't run full scans more than a couple of times a day.
