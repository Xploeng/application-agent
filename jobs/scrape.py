"""Collect new job postings for find-jobs.

Usage: uv run jobs/scrape.py

Reads data/preferences.toml, calls JobSpy for each search term, location and
site, keeps only new unique postings, and writes a temp dir for the job-evaluator agent:
  jobs.json    [{id, source, title, company, location, date, url}]
  <id>.txt     posting description
  context.md   what the user wants + digest of past decisions
"""

import json
import re
import sqlite3
import sys
import tempfile
import tomllib
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tracking.db import ROOT, connect  # noqa: E402

PREFS_PATH = ROOT / "data" / "preferences.toml"
DIGEST_LIMIT = 30
CAP = 50  # postings per search term per site
DEFAULT_SITES = ["indeed", "linkedin", "glassdoor", "google"]  # the JobSpy sites that cover Germany
LIKED = ("to_apply", "applied", "interview", "offer", "rejected")  # rejected: the user did apply


def load_prefs(path: Path = PREFS_PATH) -> dict:
    if not path.exists():
        sys.exit(f"No preferences at {path}: run /grill-preferences first.")
    with path.open("rb") as f:
        return tomllib.load(f)


def canonical_url(url: str) -> str:
    """One URL per job: platform job ids kept, tracking parameters dropped."""
    parts = urllib.parse.urlsplit(url.strip())
    host = parts.netloc.lower()
    if "linkedin.com" in host and (m := re.search(r"/jobs/view/(?:[^/?]*?-)?(\d+)", parts.path)):
        return f"https://www.linkedin.com/jobs/view/{m.group(1)}/"
    if "indeed." in host and (jk := urllib.parse.parse_qs(parts.query).get("jk")):
        return f"https://de.indeed.com/viewjob?jk={jk[0]}"
    return urllib.parse.urlunsplit((parts.scheme or "https", host, parts.path, "", ""))


def _clean(value) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None  # NaN/None -> None


def _date(value) -> str | None:
    """YYYY-MM-DD from a date/Timestamp/string; None for NaN/NaT/missing."""
    s = str(value)[:10]
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


def fetch(site: str, term: str, location: str, radius_km: int, max_age_days: int) -> list[dict]:
    """One JobSpy call, normalised to {source, title, company, location, url, date, description}."""
    from jobspy import scrape_jobs  # heavy import (pandas), only when used

    df = scrape_jobs(
        site_name=[site], search_term=term, google_search_term=f"{term} jobs near {location}",
        location=location, distance=max(1, round(radius_km / 1.609)), results_wanted=CAP,
        hours_old=max_age_days * 24, country_indeed="germany", fetch_description=True,
        description_format="markdown", verbose=0,
    )
    return [{"source": site, "title": _clean(r.get("title")) or "", "company": _clean(r.get("company")) or "",
             "location": _clean(r.get("location")), "url": canonical_url(r["job_url"]),
             "date": _date(r.get("date_posted")),
             "description": _clean(r.get("description")) or ""}
            for r in df.to_dict("records")[:CAP] if isinstance(r.get("job_url"), str)]


def collect(prefs: dict) -> tuple[list[dict], list[str]]:
    """Call JobSpy per term, location and site; one site failing never stops the others.

    Per-site calls because scrape_jobs aborts entirely if any one site raises.
    """
    search = prefs.get("search", {})
    age = search.get("max_age_days", 7)
    postings, counts, failures = [], {}, {}
    for term in search.get("terms", []):
        for loc in search.get("locations", []):
            for site in search.get("sites", DEFAULT_SITES):
                try:
                    found = fetch(site, term, loc["name"], loc.get("radius_km", 30), age)
                except Exception as e:  # report and move on
                    failures[site] = f"{type(e).__name__}: {e}"[:200]
                    continue
                postings += found
                counts[site] = counts.get(site, 0) + len(found)
    summary = [f"{site}: {n}" for site, n in counts.items()]
    summary += [f"{site}: FAILED ({err})" for site, err in failures.items() if site not in counts]
    return postings, summary


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\(m/w/d\)|\(w/m/d\)|\(f/m/d\)|\(m/f/d\)|\(all genders\)", "", s.lower())).strip()


def excluded(company: str, names: list[str]) -> bool:
    """Company matches a blocklist entry as whole words, case-insensitive ("Umbrella GmbH" matches "umbrella")."""
    return any(re.search(rf"\b{re.escape(n.lower())}\b", company.lower()) for n in names)


def filter_new(postings: list[dict], known_urls: set[str], max_age_days: int, today: date,
               known_keys: set[tuple] = frozenset()) -> list[dict]:
    """Drop too old, already tracked (any status, by URL or company+title), and in-run duplicates (keep longest text)."""
    cutoff = (today - timedelta(days=max_age_days)).isoformat()
    best: dict[tuple, dict] = {}
    seen_urls = set()
    for p in postings:
        if (p["date"] and p["date"] < cutoff) or p["url"] in known_urls or p["url"] in seen_urls:
            continue
        seen_urls.add(p["url"])
        key = (_norm(p["company"]), _norm(p["title"]))
        if key in known_keys:  # same job posted per location gets a new URL each time
            continue
        if key not in best or len(p["description"]) > len(best[key]["description"]):
            best[key] = p
    return list(best.values())


def known_urls(conn: sqlite3.Connection) -> set[str]:
    return {canonical_url(u) for (u,) in conn.execute("SELECT url FROM applications WHERE url IS NOT NULL")}


def known_keys(conn: sqlite3.Connection) -> set[tuple]:
    return {(_norm(c), _norm(r)) for c, r in conn.execute("SELECT company, role FROM applications")}


def build_digest(conn: sqlite3.Connection, limit: int = DIGEST_LIMIT) -> str:
    marks = ",".join("?" * len(LIKED))
    liked = conn.execute(
        f"SELECT role, company, location, work_mode, focus FROM applications WHERE status IN ({marks}) "
        "ORDER BY updated_at DESC, id DESC LIMIT ?", (*LIKED, limit)).fetchall()
    passed = conn.execute(
        "SELECT a.role, a.company, (SELECT detail FROM events e WHERE e.application_id = a.id AND e.kind = 'note' "
        "AND e.source = 'review' ORDER BY e.id DESC LIMIT 1) FROM applications a WHERE a.status = 'dismissed' "
        "ORDER BY a.updated_at DESC, a.id DESC LIMIT ?", (limit,)).fetchall()
    lines = ["## Past decisions", "", "Examples of past decisions. Patterns, not rules. When unsure, keep.", "",
             "Liked (wanted to apply or applied):"]
    for role, company, location, work_mode, focus in liked:
        extra = ", ".join(filter(None, [location, work_mode, f"focus: {focus}" if focus else None]))
        lines.append(f"+ {role} @ {company}" + (f" - {extra}" if extra else ""))
    lines += ["", "Passed on (dismissed by the user):"]
    lines += [f"- {role} @ {company} - {reason or 'no reason given'}" for role, company, reason in passed] or ["(none yet)"]
    return "\n".join(lines)


def write_run(postings: list[dict], want: str, digest: str) -> Path:
    out = Path(tempfile.mkdtemp(prefix="jobs-"))
    index = []
    for i, p in enumerate(postings, 1):
        job_id = f"j{i}"
        (out / f"{job_id}.txt").write_text(p["description"])
        index.append({"id": job_id, **{k: p[k] for k in ("source", "title", "company", "location", "date", "url")}})
    (out / "jobs.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    (out / "context.md").write_text(f"## What the user wants\n\n{want.strip()}\n\n{digest}\n")
    return out


def main() -> None:
    prefs = load_prefs()
    postings, summary = collect(prefs)
    blocked = prefs.get("search", {}).get("exclude_companies", [])
    conn = connect()
    try:
        new = filter_new([p for p in postings if not excluded(p["company"], blocked)], known_urls(conn), prefs.get("search", {}).get("max_age_days", 7), date.today(),
                         known_keys(conn))
        digest = build_digest(conn)
    finally:
        conn.close()
    out = write_run(new, prefs.get("evaluator", {}).get("want", ""), digest)
    print(f"dir: {out}")
    print("sites: " + ("; ".join(summary) or "none"))
    print(f"collected: {len(postings)}")
    print(f"new: {len(new)}")


if __name__ == "__main__":
    main()
