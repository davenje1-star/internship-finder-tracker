"""Conservative suggestions for recruiting email previews; never saves records."""
import re
from email.utils import parseaddr
from .email_helpers import is_rejection, suggest_company


def clean_text(text):
    return " ".join((text or "").split())


def detect_company(subject, sender, body, known_companies=()):
    _, address = parseaddr(sender)
    domain = address.rsplit("@", 1)[-1].casefold() if "@" in address else ""
    if domain == "bofa.com" or domain.endswith(".bofa.com"):
        return "Bank of America"
    text = clean_text(f"{subject} {sender} {body}")
    if re.search(r"\bbank\s+of\s+america\b", text, re.I):
        return "Bank of America"

    # Match tracked company names as complete phrases; don't select a role.
    matches = {}
    for name in known_companies:
        name = clean_text(name)
        if len(name) < 3:
            continue
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
        if re.search(pattern, text, re.I):
            matches.setdefault(name.casefold(), name)
    if len(matches) == 1:
        return next(iter(matches.values()))
    if len(matches) > 1:
        return ""
    company = clean_text(suggest_company(clean_text(subject), sender))
    if company.casefold() in {"", "noreply", "no-reply", "careers", "recruiting", "notifications", "talent acquisition"}:
        return ""
    return company[:200]


def detect_status(subject, body):
    text = clean_text(f"{subject} {body}").replace("’", "'")
    if is_rejection(text) or re.search(
        r"(?:will|have|has) not (?:be )?(?:moving|move|proceeding|proceed|progressing) (?:forward|with)|"
        r"decided not to (?:move|proceed)|"
        r"(?:unable to|will not) offer you|"
        r"application (?:was|has been) (?:unsuccessful|rejected)|"
        r"not (?:been )?selected for (?:this|the) (?:role|position)", text, re.I
    ):
        return "Rejected"
    if re.search(r"(?:assessment|coding test) invitation|(?:invite|invited|invitation).*?(?:assessment|coding test)|"
                 r"(?:complete|take) (?:the |an |our |your )?(?:online |coding |technical )?(?:assessment|coding test)", text, re.I):
        return "Assessment"
    if re.search(r"interview invitation|(?:invite|invited|invitation).*?interview|"
                 r"(?:schedule|scheduling|scheduled) (?:an |your |the )?interview", text, re.I):
        return "Interview"
    if re.search(
        r"thank you for applying|thanks for applying|"
        r"application received|(?:successfully )?received your (?:application|resume)|"
        r"application (?:has been|was|is) (?:successfully )?received|"
        r"successfully submitted your application", text, re.I
    ):
        return "Applied"
    return ""


def review_notes(company, role, status):
    notes = []
    if not company:
        notes.append("Company could not be identified confidently. Enter it or select an existing application.")
    if not role:
        notes.append("No recognizable role title was found in this email. Enter the title from the posting or select an existing application.")
    if not status:
        notes.append("No clear recruiting stage was detected. Choose the status after reviewing the email.")
    if status == "Applied":
        notes.append("This appears to confirm receipt. Verify the actual submission date; the email date may differ.")
    return notes
