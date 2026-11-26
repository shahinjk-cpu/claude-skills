# Job sources: what actually works

Tested 2026-11-25 with plain fetches (no browser, no login, no workarounds) on ~110 platforms, then in two full end-to-end runs (Berlin, Lausanne). Templates marked **(e2e)** were confirmed to filter correctly in those runs; the others returned listings once. Blocks change and depend on the network you run from: if a ✅ source fails, say so in the reply and move on. PRs with re-test results are welcome.

Legend: ✅ works with a plain fetch · 🔑 works with a free API key the user registers · 📧 blocked for automated reading, use the site's **email alerts** · ⚠️ loads but listings are incomplete (JavaScript-only, few results, no dates) · ❌ gone

## How to cover a country completely

Use the tiers in order. Count each source's results for the reply.

**Repost dates.** Many boards reset an ad's date when it's re-posted (jobscout24, itjobs.ch, Himalayas). When the same job exists on a source with a first-publication field (jobs.ch `initialPublicationDate`, BA `datumErsteVeroeffentlichung`, Greenhouse `first_published`), that date wins.

**Request budgets.** Default: at most 40 requests per site per run, about 2 seconds apart. Sources below give their own budget when they rate-limit sooner. Spend it on core keywords first, then full titles.

**Short names** for the reply's source line are in brackets, e.g. [BA], [StepStone].

1. **Open APIs (no key):** structured, dated, complete. Always use the ones for the user's country. Call JSON APIs with `curl -s` (the web-fetch tool can't send headers and summarizes big JSON). Send only the documented headers, and keep `curl`'s default user agent: never pretend to be a browser.
2. **Free-key APIs:** only if the user put a key in an environment variable (never in `profile.md`). Offer them during setup when they'd fill a gap.
3. **Job boards that render in the page:** use the URL templates below.
   - **Search terms:** each target title AND the short core keywords from the profile (e.g. `Python`, `React`, `développeur`, `Entwickler`). Exact multi-word titles often return 0.
   - **Cities:** run city-filtered boards once per city in the profile's search-area list, then dedupe.
   - **Paging:** if the source is newest-first, page until results are older than the cutoff. If it isn't (most boards: relevance order), read up to the page cap and filter by date yourself; stop early when 2 consecutive pages are entirely older than the cutoff or off-topic.
   - **Feeds without search** (Remote OK, We Work Remotely, Working Nomads, Arbeitnow, HN, ATS APIs): fetch once, filter titles and keywords locally.
4. **Email alerts** (📧): the only complete route to the biggest boards (Indeed, Glassdoor, LinkedIn beyond the first 60, SEEK, Naukri…). During setup, list the ones for the user's country and ask them to subscribe with their target titles. With a mail connector, alerts become the main source.
5. **Target companies:** if the user names companies they want, find which applicant-tracking system each careers page uses and read its public job-board API (see "Company career pages"). These are offers many boards never get.

**Web search is not a job source.** It returns board result pages and stale or fake posts. Use it only to find a company's careers page.

## Global and remote (all ✅ unless marked)

| Source | Call | Date field |
|---|---|---|
| [Himalayas] (remote) (e2e) | **Budget: 25 requests, core keywords only, ≤ 3 pages each** (429 after ~33 in testing). **Search:** `https://himalayas.app/jobs/api/search?q={q}&country={Country}&page={n}` (20 per page, not date-sorted). Skip `employmentType: "Contractor"` unless the profile accepts it. `locationRestrictions` containing the user's country, or empty (= worldwide), counts as remote confirmed for scoring. Himalayas' job pages are behind a bot check for scripts (fine in a browser): score from the API's description field. **Dates are unreliable:** in testing, 60% of results shared one re-index date, so Himalayas ads are usually "(date unverified)". Treat it as a remote-jobs extra, not a main source. Don't use the plain `/jobs/api` browse feed: 20 per call, ~1 hour of postings per 10 pages. `pubDate` gets reset by re-indexing: if the employer has a Greenhouse/Lever board, check its real first-published date; drop ads mentioning past dates | `pubDate` (Unix s) |
| [RemoteOK] | `https://remoteok.com/api` (skip element 0, a legal notice). Only the latest ~100 jobs (~5 days), mostly US-only: read each ad's location. For non-US profiles, expect almost nothing (0 usable in both European test runs); it costs 1 request, so keep it. Terms: link back to Remote OK | `date` (ISO) |
| [WWR] (e2e) | RSS per category: `https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss`, `…/remote-front-end-programming-jobs.rss`, `…/remote-full-stack-programming-jobs.rss`. Avoid `remote-programming-jobs` (stale). The `region` field is unreliable ("Anywhere" ads that say US-only): read the description in the feed. Job pages are behind a bot check; the feed's description is the ad | `pubDate` |
| Working Nomads | `https://www.workingnomads.com/api/exposed_jobs/` (single small array, filter `category_name` yourself) | `pub_date` |
| [Arbeitnow] (mostly DE) (e2e) | `https://www.arbeitnow.com/api/job-board-api?page={n}`: no search parameter, 200–300 jobs per page, pages overlap. Budget 15 pages (10 didn't cover 7 days in testing), not strictly date-ordered, `remote:true` isn't country-aware. Use for Germany; filter locally; dedupe by `slug` | `created_at` (Unix s) |
| [HN] "Who is hiring" (monthly, tech) | Find this month's thread: `https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=3` (title starts "Ask HN: Who is hiring"), then comments: `https://hn.algolia.com/api/v1/search_by_date?tags=comment,story_{objectID}&hitsPerPage=1000`, keep only `parent_id == objectID`, and drop job-seeker posts (they start with "Location:" and "Willing to relocate"). One comment can list several roles: score the best match. Watch for look-alike place names (Freiburg DE ≠ Fribourg CH). **Exempt from the 7-day window:** on the first run read the whole current thread; later, comments since `last_run` | `created_at` |
| LinkedIn 📧 | **Don't fetch.** In both end-to-end runs it answered 429 (rate limit) within a few requests, and full ads need a login. Use its job-alert emails | — |
| Remotive | Don't use: terms allow 4 calls a day with a 24 h delay, and forbid redistributing | — |
| Adzuna 🔑 (aggregator, ~12–19 countries incl. US, UK, CA, AU, IN, BR, DE, FR) | Free developer key, `ADZUNA_APP_ID` + `ADZUNA_APP_KEY`. *Not yet verified: test before relying on it* | — |
| Indeed, Glassdoor, ZipRecruiter, Careerjet | 📧 alerts only (403 / bot check everywhere) | — |

## Company career pages (applicant-tracking systems, all ✅, no key)

Find the system from the careers page link (`boards.greenhouse.io/{token}`, `jobs.lever.co/{company}`, `jobs.ashbyhq.com/{org}`, `jobs.smartrecruiters.com/{company}`, `apply.workable.com/{account}`). Slugs are not always the company name. A wrong slug gives 404 on Greenhouse/Lever/Ashby but **200 with an empty list** on SmartRecruiters and Workable: an empty list for a company that clearly hires means a wrong slug. Big companies often split boards by entity: check the jobs' locations match what you expected.

On the **first run, list every open role** at target companies that matches the profile, whatever its age. Later runs: new ones only.

**Own careers site:** if the page lists jobs in plain HTML (e.g. jobs.zalando.com), one plain fetch per run is fine. If it's a JavaScript page or Workday, SuccessFactors, Taleo or iCIMS: no API is used. Company-name searches on boards are unreliable (on jobs.ch, `term=Swisscom` returned 0 while Swisscom had live ads elsewhere), so don't rely on them: tell the user to create the company's own job alert, and match the company's name in everything else you collect. Count these under [Companies].

| System | Call | Date field |
|---|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{token}/jobs` (`?content=true` adds descriptions) | `first_published` (`updated_at` changes daily: ignore it) |
| Lever | `https://api.lever.co/v0/postings/{company}?mode=json` (EU: `api.eu.lever.co`) | `createdAt` (ms) |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{org}` (can be >10 MB) | `publishedAt` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/{id}/postings?limit=100&offset={n}` | `releasedDate` |
| Workable | `https://apply.workable.com/api/v1/widget/accounts/{account}` | `published_on` |


## United States
- ✅ **Dice** (tech): `https://www.dice.com/jobs?q={q}&location={city}&filters.postedDate=SEVEN&page={n}` (`ONE`/`THREE`/`SEVEN` days), ~20–30 per page
- ✅ **Built In** (tech): `https://builtin.com/jobs?search={q}&city={City}&state={State}&country=USA&allLocations=true&page={n}`, 25 per page
- ✅ **Wellfound** (startups): `https://wellfound.com/role/l/{role-slug}/{city-slug}?page={n}`, ~50 per page, no date sort
- ⚠️ SimplyHired (20 per page, cursor paging, few dates) · ⚠️ USAJOBS site (returned 0); 🔑 USAJOBS API, free key from developer.usajobs.gov · ⚠️ YC Work at a Startup (JavaScript, login)
- 📧 Indeed, LinkedIn, Glassdoor, ZipRecruiter, Monster, CareerBuilder

## Canada
- ✅ **Job Bank**: `https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring={q}&locationstring={City}%2C+{PROV}&sort=D&page={n}`, or RSS `https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed?searchstring={q}&locationstring={city}&sort=D&rows=100`
- 📧 Workopolis, Indeed CA, LinkedIn

## Latin America
- ✅ **Get on Board** (tech, API): `https://www.getonbrd.com/api/v0/search/jobs?query={q}&per_page=100&page={n}`; date `attributes.published_at` (Unix s)
- 📧 Catho (BR), Computrabajo (MX: empty pages), Indeed

## Switzerland
- ✅ **[jobs.ch]** (e2e): `https://www.jobs.ch/en/vacancies/?term={q}&location={city}&page={n}`, 20 per page, relevance order. `location` searches **around** a town (Genève also returns Meyrin and Onex; Zürich returns Winterthur), with local spellings (Zürich, Genève). Small towns can return 0: run the main cities of the search area only, and keep ~10 requests of the budget for opening ads. Parse the `__INIT__` JSON in the page; use `initialPublicationDate` for the age (`publicationDate` changes on reposts). Full ad: the JobPosting JSON-LD on the ad page. Open ads in the original language, not `/en/` (machine-translated, hides the real language requirements): `https://www.jobs.ch/fr/offres-emplois/detail/{id}/` or `https://www.jobs.ch/de/stellenangebote/detail/{id}/` (`/fr/vacancies/…` is a 404). French titles are often inclusive ("Développeur·euse") and miss a plain `développeur` search: core tech keywords (`Python`, `React`) find them reliably
- **[jobup]** (e2e): same listings as jobs.ch (same company, same job IDs), and jobs.ch handles French terms too. Use jobup only if jobs.ch is blocked. Template: `https://www.jobup.ch/fr/emplois/?term={q}&location={city}&page={n}`
- ✅ **[jobscout24]** (e2e): `https://www.jobscout24.ch/de/jobs/?SearchWhat={q}&p={n}`, 20 per page. The location parameter is ignored: filter places yourself. **Same job IDs as jobs.ch** (a jobs.ch ad also opens at `https://www.jobscout24.ch/de/job/{id}/`). Its dates reset on reposts: in testing, 5 "new" cards were months old by jobs.ch's `initialPublicationDate`. Verify each candidate's date with jobs.ch's `initialPublicationDate` for the same ID (the ad page's JSON-LD `datePosted` is also the repost date). A page past the last one returns 404: that's the end, not a block. Avoid `?query=` (ignored: returns all 82,000 jobs) and the slug URL `/de/jobs/{q}/{city}/` (0 results). Overlaps heavily with jobs.ch: dedupe by company + title
- ⚠️ swissdevjobs.ch (listings but no dates), jobs.admin.ch (JavaScript), okjob.ch (no search page)
- 📧 Indeed CH, LinkedIn

## France
- ✅ **France Travail**: `https://candidat.francetravail.fr/offres/recherche?motsCles={q}&lieux={dept}D&tri=1`. The first 20 only, newest first; the API is restricted
- ✅ **HelloWork**: `https://www.hellowork.com/fr-fr/emploi/recherche.html?k={q}&l={city}&st=date&p={n}`, ~30 per page
- ✅ **Free-Work** (IT): `https://www.free-work.com/fr/tech-it/jobs?query={q}&locations=fr~{region}~{city}~~&sort=date&page={n}`, 16 per page, exact dates
- ⚠️ Welcome to the Jungle (JavaScript), Choisir le service public (JavaScript)
- 📧 APEC, Indeed FR, LinkedIn

## Germany / Austria
- ✅ **[BA] Bundesagentur für Arbeit API** (e2e, best source in Europe): `GET https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v6/jobs?was={q}&wo={city}&angebotsart=1&veroeffentlichtseit={days}&size=100&page={n}` with header `X-API-Key: jobboerse-jobsuche` (public, documented). Page starts at 1. Results are in `ergebnisliste[]`, each with `referenznummer` (= `{refnr}` below), `titel`, `arbeitgeber`, `arbeitsort`. Date: `datumErsteVeroeffentlichung`. Radius: `umkreis={km}` (default ~25 km: matches the commute belt; set it from the profile's max commute). Exact titles return little: also run core keywords (`Python`, `Backend`). Full ad: `https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}` (has JSON-LD), which is also the link to record. Avoid `v4` (403)
- ✅ **[StepStone] DE** (e2e): **budget 12 requests, ≤ 3 pages per query** (connection reset at the 7th request in one test). `https://www.stepstone.de/jobs/{q}/in-{city}?ag=age_7&page={n}` (`ag=age_7` = last 7 days, `age_1` = last day), 25 per page, **not date-sorted** (`sort=2` isn't date). Use single keywords (`python`, `backend`): compound slugs match thousands of generic jobs. Listings are in the page's embedded `"items":[…]` JSON with `datePosted` and a ~500-character summary. **Ad pages are blocked** (connection reset): score from the summary, mark "(summary only)", and prefer the same job's BA or employer link when it exists
- ✅ **karriere.at** (AT): `https://www.karriere.at/jobs/{q}/{city}`. First ~18 only (`?page=` ignored)
- ✅ Arbeitnow API (see Global)
- ⚠️ AMS (JavaScript), GermanTechJobs (no dates) · 📧 XING, Indeed DE

## United Kingdom / Ireland
- ✅ **Reed**: `https://www.reed.co.uk/jobs/{q-slug}-jobs-in-{city}?sortBy=displayDate&pageno={n}`, 25 per page. 🔑 Reed API: free key, `https://www.reed.co.uk/api/1.0/search?keywords={q}&locationName={city}&resultsToTake=100&resultsToSkip={n}`, key as the Basic-auth username
- 📧 Totaljobs, CV-Library, Civil Service Jobs, Find a job (DWP), Guardian Jobs, IrishJobs, Indeed UK. The UK is the hardest country: set up alerts

## Benelux
- ✅ **StepStone BE**: `https://www.stepstone.be/jobs/{q}/in-{city}?page={n}` (same behaviour as StepStone DE)
- ⚠️ VDAB, Actiris, Le Forem (JavaScript): 📧 their alerts · 📧 Nationale Vacaturebank, werk.nl (login), Indeed

## Spain / Portugal / Italy
- ✅ **InfoJobs ES**: `https://www.infojobs.net/jobsearch/search-results/list.xhtml?keyword={q}&provinceIds={id}&sortBy=PUBLICATION_DATE&page={n}` (Madrid = 33). Only ~5 per page render: also 📧
- ✅ **Tecnoempleo** (IT): `https://www.tecnoempleo.com/ofertas-trabajo/?te={q}&ult_24h=1&pagina={n}`, 30 per page. Filter the city yourself (`pr=` IDs are unreliable)
- ✅ **Net-Empregos** (PT): `https://www.net-empregos.com/pesquisa-empregos.asp?chaves={q}&cidade={city}`, exact dates. RSS: `https://www.net-empregos.com/rssfeed.asp`
- ❌ InfoJobs Italia (closed) · ⚠️ inPA (JavaScript) · 📧 Indeed IT/ES, LinkedIn

## Nordics / Poland
- ✅ **JobTech API** (Sweden, all Platsbanken jobs): `https://jobsearch.api.jobtechdev.se/search?q={q}%20{city}&limit=100&offset={n}&sort=pubdate-desc`. Date: `publication_date`
- ✅ **Finn.no** (NO): `https://www.finn.no/job/search?q={q}+{city}&sort=PUBLISHED_DESC&page={n}`, ~50 per page, 7 pages max. Avoid `location=` codes
- ✅ **Just Join IT** (PL, IT): `https://justjoin.it/job-offers/{city}?keyword={q}&sortBy=newest&page={n}`, ~50 per page, no dates
- ⚠️ Jobindex.dk, EURES (JavaScript) · 📧 Pracuj.pl

## Asia-Pacific
- ✅ **MyCareersFuture API** (Singapore): `https://api.mycareersfuture.gov.sg/v2/jobs?search={q}&limit=20&page={n}&sortBy=new_posting_date` (page starts at 0; stop when `results` is empty). Date: `metadata.newPostingDate`. Undocumented: may change
- ✅ **Trade Me** (NZ, small): `https://www.trademe.co.nz/a/jobs/search?search_string={q}`. Paging is unreliable; 🔑 the official API needs a registered app
- ⚠️ Wantedly (JP), Saramin/Wanted (KR), APSJobs (AU): JavaScript or no dates
- 📧 **SEEK** (AU/NZ), **JobStreet** (MY/PH), **JobsDB** (HK), Jora, and in **India** Naukri, Foundit, Instahyre and Indeed: all 403. Alerts are the only route

## Middle East / Africa
- ✅ **Bayt**: `https://www.bayt.com/en/{country}/jobs/{q-slug}-jobs-in-{city}/?page={n}`, 30 per page; last 7 days: `&filters%5bjb_last_modification_date_interval%5d%5b%5d=2`
- ✅ **Jobberman** (NG) / **BrighterMonday** (KE): `https://www.jobberman.com/jobs/{category-slug}/{city}?page={n}` (same pattern on brightermonday.co.ke), 16 per page, newest first by default
- ✅ **PNet** (ZA): `https://www.pnet.co.za/jobs/{q-slug}?ag=age_7&page={n}` (`age_1` = new today), 25 per page. Avoid `sort=2` with a city path (HTTP 500)
- 📧 GulfTalent, Naukrigulf (timeouts)

## Email alert senders (for reading alerts through a mail connector)
`jobalerts-noreply@linkedin.com` · Indeed (`alert@indeed.com`, `donotreply@match.indeed.com`) · `noreply@glassdoor.com` · ZipRecruiter · SEEK · Naukri · jobs.ch · jobup.ch · jobscout24.ch · swissdevjobs.ch · `stelle.admin.ch` · StepStone · Totaljobs · APEC · Welcome to the Jungle · Pracuj.pl. Add more from what the user receives: the sender domain is enough.
