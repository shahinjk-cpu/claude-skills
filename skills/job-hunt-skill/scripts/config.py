"""Load the workspace config: the first ```json block in <workspace>/search/filters.md, merged over defaults."""
import copy, json, os, re

DEFAULTS = {
    "profile": {"homeCountry": "", "currency": "USD"},
    "queries": [],
    "gupyTerms": [],
    "sources": {
        "remoterocketship": False, "remoteok": True, "remotive": True, "himalayas": True, "jobicy": True,
        "arbeitnow": False, "weworkremotely": True, "workingnomads": True, "getonbrd": False, "gupy": False, "hn": True, "ats": True, "perfectrole": False,
    },
    "remoteRocketship": {"apiKeyFile": "~/.config/remoterocketship/api-key", "seniority": ["mid", "senior"], "maxPages": 3},
    "roles": {
        "titleKeywords": [],
        "titleRoleWords": ["engineer", "developer", "scientist", "researcher", "specialist", "architect", "programmer"],
        "textKeywords": [],
        "minTextHits": 2,
        "excludeTitle": ["sales", "account exec", "account manager", "marketing", "recruit", "talent", "intern", "trainee",
                         "junior", "jr", "director", "vp", "head of", "teacher", "instructor", "tutor", "support",
                         "counsel", "lawyer", "nurse", "physician", "ai trainer", "annotator", "writer"],
        "excludeTitleUnlessKeyword": ["llm", "genai", "generative", "agentic", "agent", "nlp", "prompt"],
    },
    "location": {"remoteOnly": True, "allowed": [], "hybridOkCities": [], "acceptUnstated": True},
    "pay": {"floorMonthly": 0, "hoursPerMonth": 160, "maxPlausibleMonthly": 0, "floorBasis": "gross", "unlisted": "flag"},
    "person": {"residence": "", "citizenships": [], "workPermits": [], "timezone": "", "minOverlapHours": 4,
               "contracts": [], "netModel": "", "netRates": {}, "contractorBillableMonths": 11},
    "ghost": {"maxAgeDays": 60, "warnAgeDays": 35, "repostSpanDays": 21},
    "fit": {},
    "penalizeKeywords": [],
    "excludedCompanies": [],
    "excludedRoles": [],
    "skills": {"extra": []},
    "atsBoards": {"greenhouse": [], "ashby": [], "lever": [], "workable": []},
    "fallbackFxPerCurrency": {},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def private_files():
    """New files and folders are owner-only: the workspace holds personal data."""
    os.umask(0o077)


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_atomic(path, text):
    """Write via a temp file and rename, so a crash never leaves a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def load_config(workspace, require_queries=True):
    private_files()
    path = os.path.join(workspace, "search", "filters.md")
    with open(path, encoding="utf-8") as fh:
        md = fh.read()
    m = re.search(r"```json\s*(\{.*?\})\s*```", md, re.S)
    if not m:
        raise SystemExit(f"No ```json block found in {path}")
    cfg = _merge(DEFAULTS, json.loads(m.group(1)))
    if require_queries and not cfg["queries"]:
        raise SystemExit("filters.md: 'queries' is empty: add the search terms for your target role")
    return cfg
