import requests
import re
import json
from pathlib import Path
from django.core.exceptions import ValidationError
from applications.models import Application
BASE_DIR = Path(__file__).resolve().parent
try:
    with open(BASE_DIR / "seen_opportunities.json", "r", encoding="utf-8") as file:
        seen_ids = set(json.load(file))
except FileNotFoundError:
    seen_ids = set()
def fetch_jobs(company_board):
    url = f"https://api.lever.co/v0/postings/{company_board}"
    response = requests.get(url, params={"mode": "json"}, timeout=10)
    response.raise_for_status()
    return response.json()


with open(BASE_DIR / "company_boards.json", "r", encoding="utf-8") as file:
    company_boards = json.load(file)
matches = []
successful_boards = 0

for company_board in company_boards:
    try:
        jobs = fetch_jobs(company_board)
    except requests.RequestException as error:
        print(f"Could not fetch {company_board}: {error}")
        continue
    successful_boards += 1
    print(f"{company_board}: found {len(jobs)} listings")

    for job in jobs:
        title = job["text"].lower()

        if (
            "software" in title
            and re.search(r"\bintern(?:ship)?\b", title)
            and job.get("country") == "US"
        ):
            job["company_board"] = company_board
            matches.append(job)

print(f"Found {len(matches)} possible software internships")

new_count = sum(job["id"] not in seen_ids for job in matches)
print(f"{new_count} new opportunities since your previous searches.")

for number, job in enumerate(matches, start=1):
    location = job.get("categories", {}).get("location", "Unknown")

    label = "NEW" if job["id"] not in seen_ids else "SEEN"
    print(f"{number}. [{label}] {job['company_board']} — {job['text']}")
    print(f"   Location: {location}")
    print(f"   Country: {job.get('country', 'Unknown')}")
    print(f"   Apply: {job.get('applyUrl', '')}")
    print()
if successful_boards > 0:
    with open(BASE_DIR / "opportunities.json", "w", encoding="utf-8") as file:
        json.dump(matches, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(matches)} opportunities.")
    seen_ids.update(job["id"] for job in matches)

    with open(BASE_DIR / "seen_opportunities.json", "w", encoding="utf-8") as file:
        json.dump(sorted(seen_ids), file, indent=2)
else:
    print("All boards failed. Your previous opportunities file was preserved.")
print(f"Tracker contains {Application.objects.count()} applications.")

while matches:
    answer = input("Opportunity number to select, or quit: ").strip().lower()

    if answer == "quit":
        break

    if not answer.isdigit() or not 1 <= int(answer) <= len(matches):
        print("Please enter a number from the opportunity list.")
        continue

    selected = matches[int(answer) - 1]
    print(f"Selected: {selected['text']}")

    link = selected.get("applyUrl", "")
    company = selected["company_board"]
    role = selected["text"]

    if not link:
        print("This listing has no application link.")
        continue

    duplicate = (
        Application.objects.filter(link=link).exists()
        or Application.objects.filter(
            company__iexact=company,
            role__iexact=role,
        ).exists()
    )

    if duplicate:
        print("This opportunity is already in your tracker.")
        continue

    confirm = input(
        "Save this opportunity to your tracker? (yes/no): "
    ).strip().lower()

    if confirm != "yes":
        continue

    application = Application(
        company=company,
        role=role,
        status="Saved",
        date_applied=None,
        link=link,
        location=selected.get("categories", {}).get("location", "Unknown"),
    )

    try:
        application.full_clean()
        application.save()
    except ValidationError as error:
        print(f"Could not save application: {error}")
        continue

    print("Opportunity saved to Django tracker.")