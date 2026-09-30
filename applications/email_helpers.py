import re
from email.utils import parseaddr

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

def suggest_role(body):
    patterns = [
        r"Job Title:\s*(.+?)\s+Job ID:",
        r"following role:\s*(.+?)(?:\.\s|[\r\n]|$)",
        r"received your application for (?:the |our )?(.+?)(?:\s+(?:role|position|job)\b|,?\s+and (?:we|will|are)\b|[.!])",
        r"application for the role\s+(.+?)(?:\.\s|$)",
        r"(?:apply for|apply to|applying for) the (.+?) (?:position|role)\b",
        r"application to our (.+?) position\b",
        r"application for the position of (.+?) has been received",
        r"received your (?:application|resume/CV) for (?:the )?(.+?) position\b",
        r"application has been received for (.+?)(?:\.\s|$)",
        r"(?:recent application to|applying for) the (.+?) (?:position|role)\b",
        r"interest in the (.+?) (?:position|role)\b",
        r"good fit for the (.+?) position\b",
        r"open position \(\s*(.+?)\s*\)\.",
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
            role = re.sub(r"\s+\d{6,}$", "", role)

            if re.search(
                r"\b(intern|interns|internship|internships|engineer|engineering|developer)\b",
                role,
                flags=re.IGNORECASE,
            ):
                return role

    return ""

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
