from unittest.mock import patch
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from .job_sources import fetch_board, filter_jobs, get_feed, normalize, normalize_curated
from .finder_filters import matches_metro, software_title_matches
from .models import Application

BOARD = {"company": "Example", "provider": "greenhouse", "board": "example"}
RAW = {
    "id": 123456, "title": "Software Engineer Intern",
    "absolute_url": "https://example.com/jobs/123456",
    "location": {"name": "Boston, Massachusetts, United States"},
    "content": "Pursuing a bachelor's degree.",
    "updated_at": "2026-11-10T00:00:00Z",
}
CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=CACHE)
class EmployerFinderTests(TestCase):
    def setUp(self):
        cache.clear()
        self.job = normalize(RAW, BOARD, "2026-11-10T00:00:00+00:00")
        self.feed = {"jobs": [self.job], "sources": [{
            "company": "Example", "provider": "Greenhouse", "state": "available",
            "checked": "2026-11-10",
        }], "board_count": 1}

    def test_greenhouse_update_is_not_claimed_as_posting_date(self):
        self.assertEqual(self.job["date_posted"], 0)
        self.assertGreater(self.job["source_updated"], 0)

    def test_lever_and_greenhouse_have_distinct_ids(self):
        lever = normalize({
            "id": 123456, "text": "Software Intern",
            "hostedUrl": "https://jobs.lever.co/example/123456",
            "categories": {"location": "Boston, MA"}, "country": "US",
            "createdAt": 1700000000000,
        }, {**BOARD, "provider": "lever"}, "now")
        self.assertNotEqual(lever["id"], self.job["id"])
        self.assertEqual(lever["date_posted"], 1700000000)
        self.assertEqual(len(filter_jobs({"jobs": [lever]}, cities=["Boston"])), 1)

    def test_non_intern_and_unsafe_links_are_excluded(self):
        self.assertIsNone(normalize({**RAW, "title": "Senior Software Engineer"}, BOARD, "now"))
        self.assertIsNone(normalize({**RAW, "absolute_url": "javascript:alert(1)"}, BOARD, "now"))

    def test_us_metro_software_and_degree_filters(self):
        self.assertEqual(len(filter_jobs(self.feed, cities=["Boston"], software_only=True)), 1)
        self.assertEqual(filter_jobs(self.feed, cities=["Atlanta"]), [])
        self.assertEqual(filter_jobs(self.feed, company="other"), [])
        grad = normalize({**RAW, "content": "Must be pursuing a PhD."}, BOARD, "now")
        self.assertEqual(filter_jobs({"jobs": [grad]}, hide_graduate=True), [])
        alternatives = normalize({**RAW, "content": "Pursuing a bachelor's or master's degree."}, BOARD, "now")
        self.assertEqual(len(filter_jobs({"jobs": [alternatives]}, hide_graduate=True)), 1)
        foreign = {**self.job, "locations": ["London, UK"]}
        self.assertEqual(filter_jobs({"jobs": [foreign]}), [])

    @patch("applications.job_sources.requests.get")
    def test_cache_and_stale_fallback_are_labeled_on_repeated_calls(self, get):
        get.return_value.json.return_value = {"jobs": [RAW]}
        initial = fetch_board(BOARD)
        fetch_board(BOARD)
        self.assertEqual(get.call_count, 1)
        # Expire only the fresh entry while preserving the last successful snapshot.
        from hashlib import sha256
        import json
        key = "employer_board_v2_" + sha256(json.dumps(BOARD, sort_keys=True).encode()).hexdigest()
        cache.delete(key)
        get.side_effect = requests.Timeout()
        for _ in range(2):
            result = fetch_board(BOARD)
            self.assertTrue(result["stale"])
            self.assertTrue(result["failed"])
            self.assertEqual(result["jobs"], initial["jobs"])

    @patch("applications.job_sources.requests.get")
    def test_invalid_response_does_not_crash(self, get):
        get.return_value.json.return_value = {"unexpected": []}
        self.assertTrue(fetch_board(BOARD)["failed"])

    @patch("applications.job_sources.fetch_curated", return_value={
        "jobs": [], "stale": False, "failed": True, "fetched_at": "",
    })
    @patch("applications.job_sources.employer_boards", return_value=[BOARD, {**BOARD, "board": "other"}])
    @patch("applications.job_sources.fetch_board")
    def test_partial_failure_and_duplicate_links(self, fetch, boards, curated):
        fetch.side_effect = [
            {"jobs": [self.job], "company": "Example", "stale": False, "failed": False, "fetched_at": "now"},
            {"jobs": [self.job], "company": "Other", "stale": True, "failed": True, "fetched_at": "then"},
        ]
        result = get_feed()
        self.assertEqual(len(result["jobs"]), 1)
        self.assertEqual(result["sources"][1]["state"], "stale")

    @patch("applications.job_sources.employer_boards", return_value=[BOARD])
    @patch("applications.job_sources.fetch_board")
    @patch("applications.job_sources.fetch_curated")
    def test_combines_sources_without_duplicate_postings(self, curated, board, boards):
        direct = {**self.job, "link": "https://example.com/careers?gh_jid=123456",
                  "locations": ["Toronto, ON, CA • Boston, MA"]}
        board.return_value = {"jobs": [direct], "stale": False, "failed": False, "fetched_at": "now"}
        listing = {
            "id": "shared", "active": True, "is_visible": True, "terms": ["Summer 2027"],
            "category": "Software", "title": direct["role"], "company_name": "Example",
            "url": "https://job-boards.greenhouse.io/example/jobs/123456?utm_source=feed",
            "locations": ["Boston, MA"],
        }
        unknown_term = normalize_curated({**listing, "terms": ["N/A"]}, "now")
        self.assertIsNotNone(unknown_term)
        self.assertFalse(unknown_term["summer_2027"])
        second = {**listing, "id": "additional", "category": "Hardware",
                  "url": "https://job-boards.greenhouse.io/example/jobs/123457"}
        self.assertIsNone(normalize_curated({**listing, "active": False}, "now"))
        self.assertIsNone(normalize_curated({**listing, "terms": ["Fall 2027"]}, "now"))
        curated.return_value = {
            "jobs": [normalize_curated(row, "now") for row in (listing, second)],
            "stale": False, "failed": False, "fetched_at": "now",
        }

        jobs = filter_jobs(get_feed(), software_only=True)

        self.assertEqual(len(jobs), 2)
        self.assertTrue(all(job["summer_2027"] for job in jobs))
        self.assertEqual({job["location"] for job in jobs}, {"Boston, MA"})
        self.assertEqual({job["source"] for job in jobs}, {"Greenhouse", "Pitt CSC & Simplify"})

    @patch("applications.demo_finder_views.get_feed")
    def test_public_search_is_read_only_and_uses_shared_feed(self, get):
        get.return_value = self.feed
        response = self.client.get(reverse("public_finder"), {"search": "1", "cities": "Boston"})
        self.assertContains(response, "Software Engineer Intern")
        self.assertContains(response, "Greenhouse")
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(self.client.post(reverse("public_finder")).status_code, 405)

    @patch("applications.job_sources.get_feed")
    def test_private_search_save_duplicates_and_ownership(self, get):
        get.return_value = self.feed
        user = get_user_model().objects.create_user(username="owner", is_staff=True)
        other = get_user_model().objects.create_user(username="other", is_staff=True)
        self.client.force_login(user)
        Application.objects.create(owner=other, company="Example", role=self.job["role"],
                                   link=self.job["link"])
        self.client.post(reverse("internship_finder"), {"action": "search"})
        response = self.client.get(reverse("internship_finder"))
        self.assertContains(response, "Software Engineer Intern")
        for _ in range(2):
            self.client.post(reverse("internship_finder"),
                             {"action": "save", "job_id": self.job["id"]})
        self.assertEqual(Application.objects.filter(owner=user).count(), 1)
        self.assertEqual(Application.objects.get(owner=user).status, "Saved")
        self.client.logout()
        self.assertEqual(self.client.get(reverse("internship_finder")).status_code, 302)

    def test_expanded_metros_include_nearby_cities(self):
        for location, metro in (
            ("Lewisville, TX", "Dallas–Fort Worth"),
            ("Buford, Georgia", "Atlanta"),
            ("Cedar Park, TX", "Austin"),
            ("Louisville, KY", "Louisville"),
            ("Jeffersonville, IN", "Louisville"),
            ("Louisville, CO", "Denver–Boulder"),
            ("Vancouver, WA", "Portland"),
            ("Schertz, TX", "San Antonio"),
        ):
            with self.subTest(location=location):
                self.assertTrue(matches_metro(location, metro))
        self.assertFalse(matches_metro("Houston, TX", "Dallas–Fort Worth"))
        self.assertFalse(matches_metro("Louisville, CO", "Louisville"))
        self.assertFalse(matches_metro("New Albany, KY", "Louisville"))

    def test_software_title_variants(self):
        for title in (
            "Software Developer Intern", "Application Development Intern",
            "Backend Engineer Intern", "Front-End Developer Co-op",
            "Full Stack Developer Intern", "iOS Engineer Intern", "Developer Intern",
            "Programmer Intern", "Engineering Intern - Developer", "SWE Intern",
        ):
            with self.subTest(title=title):
                self.assertTrue(software_title_matches(title))
                self.assertIsNotNone(normalize({**RAW, "title": title}, BOARD, "now"))
        for title in ("Business Development Intern", "Mechanical Engineer Intern",
                      "Product Development Intern", "Web Design Intern", "Engineering Intern"):
            with self.subTest(title=title):
                self.assertFalse(software_title_matches(title))

    def test_preferred_degree_is_retained(self):
        job = normalize({**RAW, "content": "Master's degree preferred. Strong Python skills required."}, BOARD, "now")
        self.assertFalse(job["graduate_required"])

    def test_query_job_ids_remain_distinct_and_bad_urls_are_dropped(self):
        first = normalize({**RAW, "absolute_url": "https://example.com/careers?job=1"}, BOARD, "now")
        second = normalize({**RAW, "absolute_url": "https://example.com/careers?job=2"}, BOARD, "now")
        self.assertNotEqual(first["link"], second["link"])
        self.assertIsNone(normalize({**RAW, "absolute_url": "https://["}, BOARD, "now"))

    @patch("applications.demo_finder_views.get_feed")
    def test_public_pagination_keeps_filters(self, get):
        get.return_value = {**self.feed, "jobs": [
            {**self.job, "id": str(i), "link": f"https://example.com/job/{i}"}
            for i in range(26)
        ]}
        response = self.client.get(reverse("public_finder"),
                                   {"search": "1", "company": "Example", "cities": "Boston", "page": "2"})
        self.assertEqual(len(response.context["jobs"]), 1)
        self.assertContains(response, "company=Example")


class ApplicationProgressTests(TestCase):
    def test_chart_starts_at_applied_and_puts_outcomes_below_progress(self):
        from dataclasses import replace
        from .dashboard_views import application_path, build_flow
        from .demo_views import DemoHistory, sample_applications

        applications = sample_applications()
        imported = replace(applications[0], status="Rejected", status_history=DemoHistory(()))
        self.assertEqual(application_path(imported), [(0, "Applied"), (1, "Rejected")])

        flow = build_flow([*applications, imported])
        nodes = flow["nodes"]
        applied = next(node for node in nodes if node["label"] == "Applied")
        self.assertEqual(applied["count"], 14)
        self.assertEqual(applied["width"], 30)
        self.assertTrue(all(node["width"] == 16 for node in nodes if node is not applied))
        for link in flow["links"]:
            if link["label"].startswith("Applied →"):
                self.assertTrue(link["path"].startswith(f'M {applied["x"] + applied["width"]} '))
        self.assertEqual(applied["x"], min(node["x"] for node in nodes))
        rejected = [node for node in nodes if node["label"] == "Rejected"]
        ghosted = next(node for node in nodes if node["label"] == "Ghosted")
        progress = [node for node in nodes if node["label"] not in {"Rejected", "Ghosted"}]
        progress_bottom = max(node["y"] + node["height"] for node in progress)
        rejected_bottom = max(node["y"] + node["height"] for node in rejected)
        self.assertGreaterEqual(min(node["y"] for node in rejected) - progress_bottom, 72)
        self.assertAlmostEqual(ghosted["y"] - rejected_bottom, 28)
        self.assertAlmostEqual(flow["height"] - ghosted["y"] - ghosted["height"], 28)
        links = {link["label"]: link["count"] for link in flow["links"]}
        self.assertEqual(links["Applied → Current: Applied"], 2)
        self.assertEqual(links["Applied → Rejected"], 2)
        self.assertEqual(links["Applied → Ghosted"], 1)
        self.assertEqual(links["Assessment → Rejected"], 1)
        self.assertEqual(links["First Interview → Rejected"], 1)
        self.assertEqual(links["Second Interview → Rejected"], 1)
