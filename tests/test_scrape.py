import json
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from jobs import scrape
from tracking.db import connect, init


def posting(url, company="Acme", title="AI Engineer", desc="", day="2026-10-15", source="indeed"):
    return {"source": source, "title": title, "company": company, "location": "München",
            "url": url, "date": day, "description": desc}


class FilterNewTest(unittest.TestCase):
    TODAY = date(2026, 10, 17)

    def test_drops_known_urls_including_dismissed(self):
        known = {"https://www.linkedin.com/jobs/view/1/"}
        out = scrape.filter_new([posting("https://www.linkedin.com/jobs/view/1/"), posting("https://x/2", company="B")],
                                known, 7, self.TODAY)
        self.assertEqual([p["url"] for p in out], ["https://x/2"])

    def test_cross_source_duplicate_keeps_longest_description(self):
        out = scrape.filter_new([posting("https://a/1", title="AI Engineer (m/w/d)", desc="short"),
                                 posting("https://b/1", company="ACME ", title="ai  engineer", desc="much longer text",
                                         source="glassdoor")], set(), 7, self.TODAY)
        self.assertEqual([p["url"] for p in out], ["https://b/1"])

    def test_age_window_and_undated(self):
        out = scrape.filter_new([posting("https://a/1", day="2026-10-01"), posting("https://b/1", company="B", day=None)],
                                set(), 7, self.TODAY)
        self.assertEqual([p["url"] for p in out], ["https://b/1"])

    def test_drops_tracked_company_title_with_new_url(self):
        out = scrape.filter_new([posting("https://ulm/2", title="AI Engineer (all genders)")], set(), 7, self.TODAY,
                                {("acme", "ai engineer")})
        self.assertEqual(out, [])

    def test_excluded_whole_word(self):
        names = ["Umbrella", "Contoso Defence"]
        self.assertTrue(scrape.excluded("Umbrella GmbH", names))
        self.assertTrue(scrape.excluded("Contoso Defence and Space", names))
        self.assertFalse(scrape.excluded("Contoso Operations", names))
        self.assertFalse(scrape.excluded("Ebwinco AG", names))

    def test_same_url_twice_in_run(self):
        out = scrape.filter_new([posting("https://a/1"), posting("https://a/1", company="Other")], set(), 7, self.TODAY)
        self.assertEqual(len(out), 1)


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "t.db"
        init(self.path)
        self.conn = connect(self.path)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def add(self, company, role, status, url=None, **extra):
        cols = ["company", "role", "status", "url", *extra]
        with self.conn:
            return self.conn.execute(f"INSERT INTO applications ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                                     (company, role, status, url, *extra.values())).lastrowid

    def test_known_urls_are_canonical(self):
        self.add("Neura", "AI Eng", "dismissed", "https://de.indeed.com/viewjob?jk=23baa&from=shareddesktop_copy")
        self.assertEqual(scrape.known_urls(self.conn), {"https://de.indeed.com/viewjob?jk=23baa"})

    def test_digest(self):
        self.add("Initech", "Agentic AI Engineer", "applied", location="Munich", work_mode="Flexible", focus="Generative")
        self.add("Globex", "RL Engineer", "rejected")
        self.add("Lead Co", "Data Engineer", "lead")
        consult = self.add("Consult AG", "AI Consultant", "dismissed")
        self.add("Quiet GmbH", "BI Analyst", "dismissed")
        with self.conn:
            self.conn.execute("INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', 'fits', 'evaluator')", (consult,))
            self.conn.execute("INSERT INTO events (application_id, kind, detail, source) VALUES (?, 'note', 'consulting', 'review')", (consult,))
        digest = scrape.build_digest(self.conn)
        self.assertIn("+ Agentic AI Engineer @ Initech - Munich, Flexible, focus: Generative", digest)
        self.assertIn("+ RL Engineer @ Globex", digest)
        self.assertNotIn("Lead Co", digest)
        self.assertIn("- AI Consultant @ Consult AG - consulting", digest)
        self.assertIn("- BI Analyst @ Quiet GmbH - no reason given", digest)
        self.assertIn("Patterns, not rules", digest)

    def test_digest_limit(self):
        for i in range(5):
            self.add(f"C{i}", "Eng", "applied")
        self.assertEqual(scrape.build_digest(self.conn, limit=2).count("\n+ "), 2)


class CanonicalUrlTest(unittest.TestCase):
    def test_linkedin_variants(self):
        for url in ("https://de.linkedin.com/jobs/view/ml-engineer-at-acme-4012345678?refId=abc&trk=x",
                    "https://www.linkedin.com/jobs/view/4012345678/"):
            self.assertEqual(scrape.canonical_url(url), "https://www.linkedin.com/jobs/view/4012345678/")

    def test_indeed_keeps_only_jk(self):
        self.assertEqual(scrape.canonical_url("https://de.indeed.com/viewjob?from=share&jk=23baa165&vjs=3"),
                         "https://de.indeed.com/viewjob?jk=23baa165")

    def test_other_urls_drop_query_and_fragment(self):
        self.assertEqual(scrape.canonical_url("https://www.glassdoor.de/job-listing/x.htm?jl=1&src=GD#a"),
                         "https://www.glassdoor.de/job-listing/x.htm")


class FetchTest(unittest.TestCase):
    def test_one_jobspy_call_normalised(self):
        import pandas as pd

        df = pd.DataFrame([
            {"job_url": "https://de.indeed.com/viewjob?jk=abc&from=x", "title": "AI Engineer", "company": "Acme",
             "location": "München, BY", "date_posted": pd.Timestamp("2026-10-15").date(), "description": float("nan")},
            {"job_url": "https://de.indeed.com/viewjob?jk=def", "title": "RL Engineer", "company": float("nan"),
             "location": None, "date_posted": float("nan"), "description": "Text"},
        ])
        with mock.patch("jobspy.scrape_jobs", return_value=df) as scrape_jobs:
            a, b = scrape.fetch("indeed", "AI Engineer", "München", 50, 7)
        kw = scrape_jobs.call_args.kwargs
        self.assertEqual((kw["site_name"], kw["distance"], kw["hours_old"], kw["results_wanted"], kw["country_indeed"]),
                         (["indeed"], 31, 168, 50, "germany"))
        self.assertEqual(a, {"source": "indeed", "title": "AI Engineer", "company": "Acme", "location": "München, BY",
                             "url": "https://de.indeed.com/viewjob?jk=abc", "date": "2026-10-15", "description": ""})
        self.assertEqual((b["company"], b["location"], b["date"], b["description"]), ("", None, None, "Text"))


class CollectAndWriteTest(unittest.TestCase):
    def test_failing_site_is_reported_others_run(self):
        prefs = {"search": {"terms": ["AI Engineer"], "locations": [{"name": "München", "radius_km": 50}],
                            "sites": ["indeed", "glassdoor"]}}

        def fake_fetch(site, *args):
            if site == "glassdoor":
                raise RuntimeError("blocked")
            return [posting("https://a/1")]

        with mock.patch.object(scrape, "fetch", side_effect=fake_fetch):
            postings, summary = scrape.collect(prefs)
        self.assertEqual(len(postings), 1)
        self.assertEqual(summary, ["indeed: 1", "glassdoor: FAILED (RuntimeError: blocked)"])

    def test_default_sites(self):
        prefs = {"search": {"terms": ["AI"], "locations": [{"name": "München"}]}}
        with mock.patch.object(scrape, "fetch", return_value=[]) as f:
            scrape.collect(prefs)
        self.assertEqual([c.args[0] for c in f.call_args_list], scrape.DEFAULT_SITES)

    def test_write_run_layout(self):
        out = scrape.write_run([posting("https://a/1", desc="Full text")], "Agentic ML", "## Past decisions")
        try:
            jobs = json.loads((out / "jobs.json").read_text())
            self.assertEqual(jobs[0]["id"], "j1")
            self.assertNotIn("description", jobs[0])
            self.assertEqual((out / "j1.txt").read_text(), "Full text")
            self.assertIn("Agentic ML", (out / "context.md").read_text())
        finally:
            shutil.rmtree(out)


if __name__ == "__main__":
    unittest.main()
