from django.db import transaction
from applications.models import Application
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
import mailbox
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime, parseaddr
from zoneinfo import ZoneInfo
import json
import re
BASE_DIR = Path(__file__).resolve().parent

def get_body(message):
    plain_parts = []
    html_parts = []

    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue

        content_type = part.get_content_type()

        if content_type not in ("text/plain", "text/html"):
            continue

        payload = part.get_payload(decode=True)

        if payload is None:
            continue

        charset = part.get_content_charset() or "utf-8"

        try:
            text = payload.decode(charset, errors="replace")
        except LookupError:
            text = payload.decode("utf-8", errors="replace")

        if content_type == "text/plain":
            if text.strip():
                plain_parts.append(text)
        else:
            soup = BeautifulSoup(text, "html.parser")

            for tag in soup(["style", "script"]):
                tag.decompose()

            text = soup.get_text(" ", strip=True)

            if text:
                html_parts.append(text)

    return "\n".join(plain_parts or html_parts)
def suggest_company(subject, sender=""):
    if subject.casefold().startswith("doordash application status"):
        return "DoorDash"
    match = re.match(
        r"^(?:thank you|thanks) for (?:applying to|your application to) (.+)",
        subject,
        flags=re.IGNORECASE,
    )

    if match:
        company = match.group(1).split(",")[0].strip().rstrip("!.")

        if not re.search(
            r"\b(intern|internship|engineer|developer)\b",
            company,
            flags=re.IGNORECASE,
        ):
            return company

    name, address = parseaddr(sender)
    name = name.strip('"')
    company_addresses = {
        "upbound@myworkday.com": "Upbound",
        "workday@bah.com": "Booz Allen Hamilton",
        "guidestone@myworkday.com": "GuideStone Financial Resources",
        "adobe@myworkday.com": "Adobe",
        "atlassian+autoreply@talent.icims.com": "Atlassian",
    }

    if address.casefold() in company_addresses:
        return company_addresses[address.casefold()]

    if subject.casefold().startswith("astranis:"):
        return "Astranis"
    aliases = {
        "WellsFargoHR": "Wells Fargo",
        "Amex Careers": "American Express",
        "EA Careers": "Electronic Arts",
        "RTX Workday Notifications": "RTX",
    }

    if name in aliases:
        return aliases[name]

    if "@" in name:
        return ""

    return re.sub(
        r"\s+(?:Careers|Recruiting|Hiring Team|Workday|Talent Acquisition|People Team)$",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip()
@transaction.atomic
def save_applications(applications):
    fields = (
        "company", "role", "status",
        "date_applied", "link", "location",
    )

    for record in applications:
        if record.get("db_id"):
            application = Application.objects.get(pk=record["db_id"])
        else:
            application = Application()

        for field in fields:
            value = record.get(field)

            if field == "date_applied":
                value = value or None
            elif field in ("link", "location"):
                value = value or ""

            setattr(application, field, value)

        application.email_metadata = {
            key: value
            for key, value in record.items()
            if key not in fields and key != "db_id"
        }

        application.full_clean()
        application.save()
        record["db_id"] = application.pk
def email_already_imported(message_id, applications):
    if not message_id:
        return False

    for item in applications:
        if message_id in (
            item.get("source_email_id"),
            item.get("last_update_email_id"),
        ):
            return True

        for event in item.get("email_history", []):
            if event.get("message_id") == message_id:
                return True

    return False
def suggest_role(body):
    patterns = [
        r"received your application for (?:the |our )?(.+?)(?:\s+(?:role|position|job)\b|,?\s+and (?:we|will|are)\b|[.!])",
        r"application for the role\s+(.+?)(?:\.\s|$)",
        r"(?:apply for|apply to|applying for) the (.+?) (?:position|role)\b",
        r"application to our (.+?) position\b",
        r"Job Title:\s*(.+?)\s+Job ID:", 
        r"application for the position of (.+?) has been received",
        r"received your (?:application|resume/CV) for (?:the )?(.+?) position\b",
        r"application has been received for (.+?)(?:\.\s|$)",
        r"(?:recent application to|applying for) the (.+?) (?:position|role)\b",
        r"interest in the (.+?) (?:position|role)\b",
        r"good fit for the (.+?) position\b",
        r"open position \(\s*(.+?)\s*\)\.",
        r"Job Title:\s*(.+?)\s+Job ID:",
        r"apply for the ([^.!]+?) position\b",
        r"applying to (?:our |the )?([^.!]+?) (?:position|role)\b",
        r"application has been received for ([^.!]+)",
        r"application for the following position:\s*(.+?) We ",
        r"job application for (.+?)\s*\(ID",
        r"applying for the role of ([^.!]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE)

        if match:
            role = match.group(1).strip(" ,.")

            if re.search(r"\b(intern|internship|engineer|developer)\b",
                         role, flags=re.IGNORECASE):
                return role

    return ""
def role_key(role):
    role = re.sub(r"^R-?\d+\s+", "", role, flags=re.IGNORECASE)
    role = re.sub(
        r"\s*\((?:Req\s*ID|ID)\s*:?\s*\d+\)",
        "",
        role,
        flags=re.IGNORECASE,
    )
    return " ".join(role.casefold().split())
def is_rejection(body):
    return bool(re.search(
        r"will not be moving (?:you forward|forward with your application)|"
        r"not move forward with (?:your application|the interview process)|"
        r"move forward with other candidates|"
        r"will not be progressing your application",
        body,
        flags=re.IGNORECASE,
    ))


def matching_role(role):
    role = role.casefold()
    role = re.sub(r"\[online assessment\]", "", role)
    role = re.sub(r"^doordash['’]s\s+", "", role)
    role = re.sub(r"\((?:req\s*id|id)\s*:?\s*\d+\)", "", role)
    return re.sub(r"[^a-z0-9]", "", role)
emails = mailbox.mbox(BASE_DIR / "NEW LABEL.mbox", create=False)
print(f"Found {len(emails)} emails")
email_records = []
for number, message in enumerate(emails, start=1):
    subject = str(make_header(decode_header(message.get("Subject", ""))))
    subject = " ".join(subject.split())
    body = get_body(message)
    body = " ".join(body.split())
    is_draft = "we saved a draft of your job application" in body.lower()
    
    sent_at = parsedate_to_datetime(message["Date"])
    sent_date = sent_at.astimezone(ZoneInfo("America/New_York")).date()
    sender = str(make_header(decode_header(message.get("From", ""))))
    email_records.append({
        "subject": subject,
        "sender": sender,
        "email_date": sent_date.isoformat(),
        "body": body,
        "is_draft": is_draft,
        "message_id": message.get("Message-ID", "").strip(),
    })
    print(f"{number}. {sent_date} - {sender} - {subject}")
emails.close()
with open(BASE_DIR / "email_records.json", "w", encoding="utf-8") as file:
    json.dump(email_records, file, indent=2, ensure_ascii=False)
print(f"Saved {len(email_records)} email records")
applications = []

for application in Application.objects.all():
    record = dict(application.email_metadata)

    record.update({
        "db_id": application.pk,
        "company": application.company,
        "role": application.role,
        "status": application.status,
        "date_applied": (
            application.date_applied.isoformat()
            if application.date_applied else None
        ),
        "link": application.link,
        "location": application.location,
    })

    applications.append(record)

print(f"Tracker contains {len(applications)} applications.")
print("\nAutomatic import preview:")

suggestions = []
needs_review = 0

for record in email_records:
    if record["is_draft"]:
        continue

    if email_already_imported(record["message_id"], applications):
        continue

    text = record["subject"] + " " + record["body"]

    rejection = re.search(
        r"will not be moving (?:you forward|forward with your application)|"
        r"not move forward with (?:your application|the interview process)|"
        r"move forward with other candidates|"
        r"will not be progressing your application",
        text,
        flags=re.IGNORECASE,
    )

    if rejection:
        needs_review += 1
        continue

    confirmation = re.search(
        r"thank you for applying|thanks for applying|"
        r"thank you for your application|"
        r"application received|application has been received|"
        r"received your application|"
        r"thanks for completing your application|"
        r"received your resume/CV|"
        r"your submission will be reviewed|"
        r"your application will be taken into careful consideration|"
        r"thank you for launching your application",
        text,
        flags=re.IGNORECASE,
    )
    if not confirmation:
        needs_review += 1
        continue

    company = suggest_company(record["subject"], record["sender"])
    role = suggest_role(record["body"])

    if not company or not role:
        needs_review += 1
        continue

    duplicate = any(
        item["company"].strip().casefold() == company.strip().casefold()
        and role_key(item["role"]) == role_key(role)
        for item in applications + suggestions
    )

    if duplicate:
        continue

    suggestions.append({
        "company": company,
        "role": role,
        "status": "Applied",
        "date_applied": record["email_date"],
        "link": "",
        "source_email_subject": record["subject"],
        "source_email_date": record["email_date"],
        "source_email_id": record["message_id"],
    })

    print(f"Suggested: {company} — {role}")

print(
    f"\n{len(suggestions)} new applications; "
    f"{needs_review} emails need review."
)

if suggestions:
    confirm = input("Import all suggestions? (yes/no): ").strip().lower()

    if confirm == "yes":
        applications.extend(suggestions)
        save_applications(applications)
        print(f"Imported {len(suggestions)} applications.")
        print(f"Tracker contains {len(applications)} applications.")
    else:
        print("Bulk import cancelled.")
print("\nAutomatic rejection update preview:")

updates = []
rejected_applications = []
unmatched = 0

for record in sorted(email_records, key=lambda item: item["email_date"]):
    if record["is_draft"]:
        continue

    if email_already_imported(record["message_id"], applications):
        continue

    if not is_rejection(record["body"]):
        continue

    company = suggest_company(record["subject"], record["sender"])
    role = suggest_role(record["body"])

    if not company or not role:
        unmatched += 1
        continue

    matches = [
        item for item in applications
        if item["company"].strip().casefold() == company.strip().casefold()
        and matching_role(item["role"]) == matching_role(role)
    ]

    # Only update when exactly one application matches.
    if not matches:
        duplicate = any(
            item["company"].strip().casefold() == company.strip().casefold()
            and matching_role(item["role"]) == matching_role(role)
            for item in rejected_applications
        )

        if not duplicate:
            rejected_applications.append({
                "company": company,
                "role": role,
                "status": "Rejected",
                "date_applied": None,
                "link": "",
                "source_email_subject": record["subject"],
                "source_email_date": record["email_date"],
                "source_email_id": record["message_id"],
                "last_update_email_id": record["message_id"],
                "last_update_email_date": record["email_date"],
            })
            print(f"Add as Rejected: {company} — {role}")

        continue

    if len(matches) > 1:
        unmatched += 1
        print(f"Multiple matches: {company} — {role}")
        continue

    selected = matches[0]
    latest_date = (
        selected.get("last_update_email_date")
        or selected.get("source_email_date")
        or selected.get("date_applied")
        or ""
    )

    # An older rejection should not overwrite a newer status.
    if record["email_date"] < latest_date:
        unmatched += 1
        continue

    # Leave conflicting offer records for manual review.
    if selected["status"] == "Offer":
        unmatched += 1
        continue

    updates.append((selected, record))
    print(
        f"{selected['company']} — {selected['role']}: "
        f"{selected['status']} → Rejected "
        f"({record['email_date']})"
    )

print(
    f"\n{len(updates)} rejection emails matched; "
    f"{unmatched} need manual review."
)

if updates:
    confirm = input(
        "Save all matched rejection updates? (yes/no): "
    ).strip().lower()

    if confirm == "yes":
        for selected, record in updates:
            selected["status"] = "Rejected"
            selected.setdefault("email_history", []).append({
                "message_id": record["message_id"],
                "email_date": record["email_date"],
                "subject": record["subject"],
                "status": "Rejected",
            })
            selected["last_update_email_id"] = record["message_id"]
            selected["last_update_email_date"] = record["email_date"]

        save_applications(applications)
        print("Rejection updates saved.")
    else:
        print("Rejection updates cancelled.")
if rejected_applications:
    confirm = input(
        f"Add {len(rejected_applications)} rejected applications? (yes/no): "
    ).strip().lower()

    if confirm == "yes":
        applications.extend(rejected_applications)
        save_applications(applications)
        print(f"Tracker contains {len(applications)} applications.")
    else:
        print("Import cancelled.")
while True:
    answer = input("Email number to review, or quit: ").strip().lower()

    if answer == "quit":
        break

    if not answer.isdigit() or not 1 <= int(answer) <= len(email_records):
        print("Please enter a number from the email list.")
        continue

    record = email_records[int(answer) - 1]
    if record["is_draft"]:
        print("This email describes an unfinished application. Choose its submission confirmation instead.")
        continue
    already_imported = email_already_imported(
        record["message_id"], applications
    )
    if already_imported:
        print("This email has already been imported.")
        continue

    print(f"\nSubject: {record['subject']}")
    print(f"Date: {record['email_date']}")
    print(f"Sender: {record['sender']}")
    print(record["body"])
    print()

    action = input("Create, update, or skip? ").strip().lower()

    if action == "skip":
        continue

    if action == "update":
        if not applications:
            print("There are no applications to update.")
            continue

        for number, item in enumerate(applications, start=1):
            print(f"{number}. {item['company']} — {item['role']} ({item['status']})")

        answer = input("Which application should this email update? ").strip()

        if not answer.isdigit() or not 1 <= int(answer) <= len(applications):
            print("Please enter a number from the application list.")
            continue

        selected = applications[int(answer) - 1]
        print(f"Selected: {selected['company']} — {selected['role']}")
        new_status = input(
            "New status (Applied/Interview/Rejected/Offer): "
        ).strip().capitalize()

        if new_status not in ("Applied", "Interview", "Rejected", "Offer"):
            print("Choose a valid status.")
            continue
        confirm = input(
            f"Change {selected['company']} - {selected['role']}"
            f"from {selected['status']} to {new_status}? (yes/no): "
        ).strip().lower()
        if confirm != 'yes':
            print("Update cancelled.")
            continue
        selected["status"] = new_status
        history = selected.setdefault("email_history", [])
        history.append({
            "message_id": record["message_id"],
            "email_date": record["email_date"],
            "subject": record["subject"],
            "status": new_status,
        })
        selected["last_update_email_id"] = record["message_id"]
        selected["last_update_email_date"] = record["email_date"]

        save_applications(applications)

        print("Application updated.")
        continue

    if action != "create":
        print("Please enter create, update, or skip.")
        continue

    suggested_company = suggest_company(record["subject"], record["sender"])
    company = input(f"Company [{suggested_company}]: ").strip() or suggested_company

    suggested_role = suggest_role(record["body"])
    role = input(f"Role [{suggested_role}]: ").strip() or suggested_role

    if not company or not role:
        print("Company and role are required.")
        continue

    date_applied = input(
        f"Date applied (YYYY-MM-DD) [{record['email_date']}]: "
    ).strip() or record["email_date"]
    try:
        date_applied = date.fromisoformat(date_applied).isoformat()
    except ValueError:
        print("Enter a valid date in YYYY-MM-DD format.")
        continue
    status = input(
        "Current status (Saved/Applied/Interview/Rejected/Offer) [Applied]: "
    ).strip().capitalize() or "Applied"
    if status not in ("Saved", "Applied", "Interview", "Rejected", "Offer"):
        print("Choose a valid status.")
        continue
    link = input("Application link (Enter to leave blank): ").strip()
    application = {
        "company": company,
        "role": role,
        "status": status,
        "date_applied": date_applied,
        "link": link,
        "source_email_subject": record["subject"],
        "source_email_date": record["email_date"],
        "source_email_id": record["message_id"],
    }

    print(application)
    duplicate = any(
        item["company"].strip().lower() == company.lower()
        and role_key(item["role"]) == role_key(role)
        for item in applications
    )

    if duplicate:
        print("This company and role are already in your tracker.")
        continue
    confirm = input("Save this application? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Import canceled.")
        continue
    applications.append(application)
    save_applications(applications)
    print("Application saved")