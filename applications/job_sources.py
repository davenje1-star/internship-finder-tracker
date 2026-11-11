"""Combine curated listings and employer boards for both finder pages."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from itertools import zip_longest
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import ijson
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from urllib3.exceptions import HTTPError as StreamHTTPError

from .finder_filters import software_title_matches

FRESH_SECONDS = 900
STALE_SECONDS = 86400
LOCKHEED_PORTAL = "https://lockheedmartin.eightfold.ai"
DISNEY_PORTAL = "https://www.disneycareers.com"
EMPLOYER_PROVIDERS = {"greenhouse", "lever", "eightfold", "disney"}
CURATED_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2027-Internships/dev/.github/scripts/listings.json"
)
CURATED_NAME = "Pitt CSC & Simplify"
SUMMER_2027 = re.compile(r"\bsummer[\s,–-]+2027\b|\b2027[\s,–-]+summer\b", re.I)
INTERNSHIP = re.compile(r"\bintern(?:ship)?\b|\bco[ -]?op\b", re.I)
TECH = re.compile(
    r"software|developer|computer|\bdata\b|machine learning|artificial intelligence|"
    r"cyber|security|\bIT\b|information technology|systems|cloud|\bQA\b|"
    r"quality assurance|robotics|firmware|embedded|\bSRE\b", re.I
)


def employer_boards():
    path = Path(settings.BASE_DIR) / "employer_boards.json"
    boards = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(boards, list) or not boards:
        raise ValueError("Configure at least one employer board.")
    for board in boards:
        if (not isinstance(board, dict)
                or board.get("provider") not in EMPLOYER_PROVIDERS
                or not isinstance(board.get("board"), str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", board["board"])
                or not isinstance(board.get("company"), str) or not board["company"]):
            raise ValueError("Invalid employer board configuration.")
    return boards


def text(value):
    if not isinstance(value, str):
        return ""
    return BeautifulSoup(unescape(value), "html.parser").get_text(" ", strip=True)


def timestamp(value):
    try:
        if isinstance(value, (int, float)):
            return value / 1000 if value > 10**11 else value
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError, OverflowError):
        return 0


def graduate_required(description):
    """Hide only explicit graduate requirements, retaining bachelor alternatives."""
    if re.search(r"bachelor|undergraduate|baccalaureate", description, re.I):
        return False
    sentences = [part for part in re.split(r"[!?;\n]|\.(?=\s|$)", description)
                 if not re.search(r"preferred|optional|nice to have", part, re.I)]
    return bool(re.search(
        r"(?:must|require[ds]?|minimum|enrolled|pursuing)[^.\n]{0,100}"
        r"(?:master['’]?s|\bph\.?d\b|doctoral)|"
        r"(?:master['’]?s|\bph\.?d\b|doctoral)[^.\n]{0,60}\brequired\b",
        " ".join(sentences), re.I
    ))


def normalize(raw, board, fetched_at):
    if not isinstance(raw, dict):
        return None
    provider = board["provider"]
    title = raw.get("title") if provider == "greenhouse" else raw.get("text")
    if not isinstance(title, str) or not INTERNSHIP.search(title):
        return None
    if not (TECH.search(title) or software_title_matches(title)):
        return None
    if provider == "greenhouse":
        title = raw.get("title")
        link = raw.get("absolute_url")
        location = raw.get("location")
        locations = [location.get("name", "")] if isinstance(location, dict) else []
        description = text(raw.get("content"))
        posted = 0  # updated_at is not a publication date
        source_updated = timestamp(raw.get("updated_at"))
    else:
        title = raw.get("text")
        link = raw.get("hostedUrl") or raw.get("applyUrl")
        categories = raw.get("categories")
        categories = categories if isinstance(categories, dict) else {}
        locations = categories.get("allLocations") or [categories.get("location", "")]
        if isinstance(locations, str):
            locations = [locations]
        if not isinstance(locations, list):
            locations = []
        if str(raw.get("country", "")).upper() == "US":
            locations = [f"{v}, United States" for v in locations if isinstance(v, str)]
        description = text(raw.get("descriptionPlain") or raw.get("description"))
        lists = raw.get("lists") or []
        if isinstance(lists, list):
            description += " " + " ".join(
                text(v.get("content")) for v in lists if isinstance(v, dict))
        posted = timestamp(raw.get("createdAt"))
        source_updated = 0
    if not isinstance(title, str) or not title or not isinstance(link, str):
        return None
    try:
        parts = urlsplit(link)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.netloc or parts.username:
        return None
    locations = [v.strip() for v in locations if isinstance(v, str) and v.strip()]
    # Query parameters can carry job IDs. Keep the full URL for safe deduplication.
    link = urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, ""))
    return {
        "id": f"{provider}:{board['board']}:{raw.get('id') or sha256(link.encode()).hexdigest()}",
        "company": board["company"], "role": title.strip(),
        "locations": locations, "link": link,
        "date_posted": posted, "source_updated": source_updated,
        "source": provider.title(), "source_board": board["board"],
        "fetched_at": fetched_at,
        "graduate_required": graduate_required(description),
        "summer_2027": bool(SUMMER_2027.search(title) or SUMMER_2027.search(description)),
    }


def fetch_special_board(provider):
    """Adapt public search results to the existing multi-location row shape."""
    if provider == "eightfold":
        response = requests.get(
            f"{LOCKHEED_PORTAL}/api/pcsx/search?domain=lockheedmartin.com"
            "&query=Software%20Engineer%20Intern&start=0&num=20", timeout=(5, 8),
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data.get("positions") if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Expected an Eightfold position list.")
        return [
            {
                "id": row["id"], "text": row.get("name"),
                "hostedUrl": f"{LOCKHEED_PORTAL}/careers/job/{row['id']}?domain=lockheedmartin.com",
                "categories": {"allLocations": row.get("locations")},
                "createdAt": row.get("postedTs"),
            }
            for row in rows if isinstance(row, dict) and str(row.get("id", "")).isdecimal()
        ]

    jobs = []
    for page in range(1, 4):
        response = requests.get(
            f"{DISNEY_PORTAL}/en/search-jobs/Summer%202027/391/1/{page}", timeout=(5, 8),
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        section = soup.select_one("#search-results")
        if section is None:
            raise ValueError("Expected a Disney careers results section.")
        cards = section.select("#search-results-jobs a[data-job-id]")
        if not cards:
            if page == 1 and section.get("data-total-job-results") != "0":
                raise ValueError("Expected Disney job cards.")
            break
        for card in cards:
            title = card.find("h2")
            location = card.select_one(".job-location")
            href = card.get("href", "")
            if title is None or location is None or not href.startswith("/en/job/"):
                continue
            jobs.append({
                "id": card["data-job-id"], "text": title.get_text(" ", strip=True),
                "hostedUrl": urljoin(DISNEY_PORTAL, href),
                "categories": {"location": re.sub(r"\s*,\s*", ", ", location.get_text(" ", strip=True))},
            })
        if int(section.get("data-total-job-results", "0")) <= page * len(cards):
            break
    return jobs


def stream_listing_rows(url, *, params=None, timeout, array_key=""):
    """Read one listing at a time from a public JSON array."""
    with requests.get(url, params=params, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        response.raw.decode_content = True
        events = ijson.parse(response.raw, use_float=True)
        if array_key:
            if next(events, None) != ("", "start_map", None):
                raise ValueError("Expected a JSON object containing listings.")
            for event in events:
                if event == (array_key, "start_array", None):
                    break
            else:
                raise ValueError("Expected a job list.")
        elif next(events, None) != ("", "start_array", None):
            raise ValueError("Expected a job list.")
        prefix = f"{array_key}.item" if array_key else "item"
        yield from ijson.items(events, prefix)


def fetch_board(board, refresh=False):
    """Return fresh data, or a labeled last-success snapshot after a failure."""
    key = "employer_board_v2_" + sha256(
        json.dumps(board, sort_keys=True).encode()).hexdigest()
    fresh = None if refresh else cache.get(key)
    if fresh is not None:
        return {"stale": False, "failed": False, **fresh}
    try:
        provider = board["provider"]
        if provider in {"eightfold", "disney"}:
            rows = fetch_special_board(provider)
        else:
            if provider == "greenhouse":
                url = f"https://boards-api.greenhouse.io/v1/boards/{board['board']}/jobs"
                params = {"content": "true"}
            else:
                url = f"https://api.lever.co/v0/postings/{board['board']}"
                params = {"mode": "json"}
            rows = stream_listing_rows(
                url, params=params, timeout=(5, 8),
                array_key="jobs" if provider == "greenhouse" else "",
            )
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        jobs = [job for row in rows if (job := normalize(row, board, fetched))]
        result = {"jobs": jobs, "company": board["company"], "fetched_at": fetched}
        cache.set(key, result, FRESH_SECONDS)
        cache.set(key + "_last", result, STALE_SECONDS)
        return {**result, "stale": False, "failed": False}
    except (requests.RequestException, StreamHTTPError, ijson.JSONError, ValueError, TypeError) as error:
        # Briefly cache failures to avoid hammering unavailable boards.
        last = cache.get(key + "_last")
        result = last or {"jobs": [], "company": board["company"], "fetched_at": ""}
        failed = {**result, "stale": bool(last), "failed": True, "error": type(error).__name__}
        cache.set(key, failed, 60)
        return failed


def normalize_curated(row, fetched_at):
    from .finder_filters import graduate_only_listing

    if not isinstance(row, dict) or row.get("active") is not True or row.get("is_visible") is not True:
        return None
    terms = row.get("terms")
    if not isinstance(terms, list):
        return None
    title, company, link = (row.get(key) for key in ("title", "company_name", "url"))
    if not all(isinstance(value, str) and value.strip() for value in (title, company, link)):
        return None
    summer_2027 = "Summer 2027" in terms
    software_title = software_title_matches(title)
    if not summer_2027 and (terms != ["N/A"] or not software_title or not INTERNSHIP.search(title)):
        return None
    if row.get("category") not in ("Software", "Software Engineering") and not software_title:
        return None
    try:
        parts = urlsplit(link)
    except ValueError:
        return None
    if parts.scheme != "https" or not parts.hostname or parts.username:
        return None
    locations = row.get("locations")
    if not isinstance(locations, list):
        return None
    return {
        "id": f"curated:{row.get('id') or sha256(link.encode()).hexdigest()}",
        "company": company.strip(),
        "role": title.strip(),
        "locations": [location.strip() for location in locations if isinstance(location, str)],
        "link": urlunsplit(parts._replace(fragment="")),
        "date_posted": timestamp(row.get("date_posted")),
        "source": CURATED_NAME,
        "fetched_at": fetched_at,
        "graduate_required": graduate_only_listing(row),
        "summer_2027": summer_2027,
    }


def fetch_curated(refresh=False):
    key = "finder_curated_summer_2027_v3"
    cached = None if refresh else cache.get(key)
    if cached is not None:
        return cached
    try:
        rows = stream_listing_rows(CURATED_URL, timeout=(5, 15))
        fetched = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = {
            "jobs": [job for row in rows if (job := normalize_curated(row, fetched))],
            "fetched_at": fetched, "stale": False, "failed": False,
        }
        cache.set(key, result, FRESH_SECONDS)
        cache.set(key + "_last", result, STALE_SECONDS)
        return result
    except (requests.RequestException, StreamHTTPError, ijson.JSONError, ValueError) as error:
        last = cache.get(key + "_last")
        result = {**(last or {"jobs": [], "fetched_at": ""}),
                  "stale": bool(last), "failed": True, "error": type(error).__name__}
        cache.set(key, result, 60)
        return result


def posting_key(link):
    parts = urlsplit(link)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith("utm_") and key.lower() not in {
                 "gh_src", "lever-source", "ref", "source", "trackingid", "fbclid", "gclid",
             }]
    host = parts.hostname or ""
    greenhouse_id = next((value for key, value in query
                          if value.isdecimal() and (key.lower() == "gh_jid"
                          or key.lower() == "token" and host == "boards.greenhouse.io")), "")
    path = parts.path.rstrip("/")
    if not greenhouse_id and host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
        match = re.search(r"/jobs/(\d+)$", path)
        greenhouse_id = match[1] if match else ""
    if greenhouse_id:
        return ("greenhouse", greenhouse_id)
    if host == "lockheedmartin.eightfold.ai":
        match = re.fullmatch(r"/careers/job/(\d+)(?:-[^/]+)?", path)
        if match:
            return ("eightfold", host, match[1])
    if host in {"disneycareers.com", "www.disneycareers.com", "jobs.disneycareers.com"}:
        match = re.search(r"/job/.+/(\d+)$", path)
        if match:
            return ("disney", match[1])
    if host in {"jobs.lever.co", "jobs.eu.lever.co"}:
        match = re.fullmatch(r"/([^/]+)/([a-f0-9-]{36})(?:/apply)?", path, re.I)
        if match:
            return ("lever", host, match[1].lower(), match[2].lower())
    return ("url", parts.netloc.lower(), path, urlencode(sorted(query)))


def get_feed(refresh=False):
    boards = employer_boards()
    with ThreadPoolExecutor(max_workers=4) as pool:
        curated = pool.submit(fetch_curated, refresh=refresh)
        results = list(pool.map(lambda board: fetch_board(board, refresh=refresh), boards))
        results.append(curated.result())
    jobs = {}
    statuses = []
    sources = [(board["company"], board["provider"].title()) for board in boards]
    sources.append((CURATED_NAME, "Summer 2027 feed"))
    for (company, provider), result in zip(sources, results, strict=True):
        statuses.append({
            "company": company, "provider": provider,
            "state": "stale" if result["stale"] else "unavailable" if result["failed"] else "available",
            "checked": result["fetched_at"],
            "error": result.get("error", ""),
        })
        for row in result["jobs"]:
            key = posting_key(row["link"])
            current = {**row, "stale": result["stale"]}
            if key not in jobs:
                jobs[key] = current
                continue
            first, second = jobs[key], current
            if first["stale"] and not second["stale"]:
                first, second = second, first
            jobs[key] = {
                **first,
                "locations": list(dict.fromkeys([*first["locations"], *second["locations"]])),
                "date_posted": max(first["date_posted"], second["date_posted"]),
                "summer_2027": first.get("summer_2027") or second.get("summer_2027"),
                "graduate_required": first["graduate_required"] or second["graduate_required"],
            }
    return {"jobs": list(jobs.values()), "sources": statuses, "board_count": len(boards)}


def filter_jobs(feed, cities=(), company="", software_only=False,
                hide_graduate=False, excluded_companies=()):
    # Import at call time to retain the existing location definitions without cycles.
    from .finder_filters import company_key, is_us_location, matches_metro
    jobs = []
    for job in feed["jobs"]:
        locations = list(dict.fromkeys(
            part.strip()
            for location in job["locations"]
            for part in re.split(r"\s*(?:;|\||•)\s*", location)
            if is_us_location(part.strip())
        ))
        if not locations or (cities and not any(
                matches_metro(v, city) for city in cities for v in locations)):
            continue
        if company.casefold() not in job["company"].casefold():
            continue
        if software_only and not software_title_matches(job["role"]):
            continue
        if hide_graduate and job["graduate_required"]:
            continue
        if company_key(job["company"]) in excluded_companies:
            continue
        jobs.append({**job, "location": "; ".join(locations)})
    jobs.sort(key=lambda row: (
        -row["date_posted"], row["company"].casefold(), row["role"].casefold(), row["id"]))
    # Mix employers before pagination while keeping each employer's newest jobs first.
    by_employer = {}
    for job in jobs:
        by_employer.setdefault(company_key(job["company"]), []).append(job)
    return [
        job
        for round_of_jobs in zip_longest(*by_employer.values())
        for job in round_of_jobs
        if job is not None
    ]
