"""Shared finder matching rules."""
import re

METRO_AREAS = {
    "Atlanta": [
        "Atlanta", "Alpharetta", "Marietta", "Duluth", "Buford", "Suwanee", "Lawrenceville",
        "Dunwoody", "Sandy Springs", "Roswell", "Johns Creek", "Peachtree Corners", "Norcross",
        "Decatur", "Kennesaw", "Smyrna", "Peachtree City", "Cumming",
    ],
    "Austin": [
        "Austin", "Round Rock", "Cedar Park", "Georgetown", "Pflugerville", "Leander", "Kyle",
        "Buda", "Hutto", "Taylor",
    ],
    "Boston": [
        "Boston", "Cambridge", "Somerville", "Waltham", "Burlington", "Bedford", "Lexington",
        "Newton", "Watertown", "Woburn", "Framingham", "Natick", "Quincy", "Needham",
        "Westford", "Andover", "Lowell", "Marlborough", "Billerica", "Chelmsford",
    ],
    "Charlotte": [
        "Charlotte", "Concord", "Huntersville", "Matthews", "Mooresville", "Gastonia",
        "Kannapolis", "Fort Mill", "Rock Hill",
    ],
    "Chicago": [
        "Chicago", "Evanston", "Schaumburg", "Naperville", "Oak Brook", "Downers Grove",
        "Rosemont", "Des Plaines", "Deerfield", "Lake Forest", "Northbrook", "Lisle", "Aurora",
        "Arlington Heights", "Rolling Meadows", "Vernon Hills",
    ],
    "Columbus": [
        "Columbus", "Dublin", "Westerville", "New Albany", "Hilliard", "Gahanna", "Worthington",
        "Grove City", "Powell", "Delaware",
    ],
    "Dallas–Fort Worth": [
        "Dallas", "Fort Worth", "Plano", "Irving", "Richardson", "Lewisville", "Arlington",
        "Frisco", "McKinney", "Allen", "Garland", "Carrollton", "Addison", "Coppell",
        "Grapevine", "Southlake", "Denton", "The Colony", "Westlake", "Roanoke",
        "Farmers Branch", "Grand Prairie", "Flower Mound", "Las Colinas",
        "Fort Worth Metroplex", "Dallas-Fort Worth", "Dallas/Fort Worth", "DFW",
    ],
    "Denver–Boulder": [
        "Denver", "Boulder", "Broomfield", "Aurora", "Westminster", "Thornton", "Longmont",
        "Louisville", "Lafayette", "Superior", "Littleton", "Centennial", "Englewood",
        "Greenwood Village", "Lakewood", "Golden", "Highlands Ranch", "Lone Tree",
    ],
    "Detroit–Ann Arbor": [
        "Detroit", "Ann Arbor", "Dearborn", "Troy", "Southfield", "Novi", "Farmington Hills",
        "Livonia", "Auburn Hills", "Pontiac", "Rochester Hills", "Warren", "Sterling Heights",
        "Plymouth", "Ypsilanti", "Canton",
    ],
    "Houston": [
        "Houston", "The Woodlands", "Sugar Land", "Katy", "Pearland", "Spring", "Cypress",
        "Stafford", "Missouri City", "Pasadena", "Webster", "League City", "Baytown", "Tomball",
    ],
    "Indianapolis": [
        "Indianapolis", "Carmel", "Westfield", "Fishers", "Noblesville", "Zionsville",
        "Whitestown", "Plainfield", "Greenwood", "Avon", "Brownsburg", "Lawrence",
    ],
    "Kansas City": [
        "Kansas City", "Overland Park", "Lenexa", "Olathe", "Shawnee", "Leawood", "Mission",
        "Merriam", "Independence", "Lee's Summit", "Liberty", "North Kansas City",
    ],
    "Los Angeles": [
        "Los Angeles", "Santa Monica", "Culver City", "Pasadena", "Burbank", "Glendale",
        "El Segundo", "Hawthorne", "Torrance", "Long Beach", "Manhattan Beach", "Redondo Beach",
        "Inglewood", "Woodland Hills", "Westlake Village", "Calabasas", "Santa Clarita",
        "Irvine", "Anaheim", "Costa Mesa", "Newport Beach", "Santa Ana", "Orange", "Fullerton",
    ],
    "Louisville": [
        "Louisville", "Jeffersontown", "St. Matthews", "Shively", "Prospect", "Shelbyville",
        "Jeffersonville", "New Albany", "Clarksville",
    ],
    "Miami–Fort Lauderdale": [
        "Miami", "Fort Lauderdale", "Boca Raton", "Doral", "Coral Gables", "Miami Beach",
        "Aventura", "Hollywood", "Plantation", "Sunrise", "Weston", "Pembroke Pines",
        "Deerfield Beach", "Pompano Beach", "Delray Beach", "West Palm Beach",
    ],
    "Minneapolis–St. Paul": [
        "Minneapolis", "St. Paul", "Saint Paul", "Bloomington", "Eden Prairie", "Minnetonka",
        "Edina", "Plymouth", "Maple Grove", "Golden Valley", "Richfield", "Eagan", "Burnsville",
        "Woodbury", "Shakopee", "Chanhassen", "Fridley", "Brooklyn Park",
    ],
    "Nashville": [
        "Nashville", "Franklin", "Brentwood", "Murfreesboro", "Smyrna", "La Vergne",
        "Mount Juliet", "Hendersonville", "Gallatin", "Lebanon", "Spring Hill",
    ],
    "New York City": [
        "New York", "NYC", "Brooklyn", "Jersey City", "Hoboken", "Manhattan", "Queens", "Bronx",
        "Staten Island", "Long Island City", "Newark", "Secaucus", "Weehawken", "Edgewater",
        "Fort Lee", "Paramus", "Parsippany", "Morristown", "White Plains", "Yonkers",
        "Purchase", "Stamford", "Greenwich",
    ],
    "Philadelphia": [
        "Philadelphia", "King of Prussia", "Conshohocken", "Wayne", "Radnor", "Malvern",
        "West Chester", "Exton", "Chesterbrook", "Horsham", "Fort Washington", "Blue Bell",
        "Plymouth Meeting", "Newtown Square", "Camden", "Cherry Hill", "Mount Laurel",
        "Wilmington",
    ],
    "Phoenix": [
        "Phoenix", "Tempe", "Scottsdale", "Chandler", "Mesa", "Gilbert", "Glendale", "Peoria",
        "Goodyear", "Surprise", "Avondale", "Tolleson", "Queen Creek",
    ],
    "Pittsburgh": [
        "Pittsburgh", "Cranberry Township", "Warrendale", "Wexford", "Moon Township",
        "Coraopolis", "Monroeville", "Canonsburg", "Southpointe", "Robinson Township",
        "Sewickley",
    ],
    "Portland": [
        "Portland", "Hillsboro", "Beaverton", "Tigard", "Tualatin", "Wilsonville",
        "Lake Oswego", "Milwaukie", "Sherwood", "Gresham", "Vancouver", "Camas",
    ],
    "Raleigh–Durham": [
        "Raleigh", "Durham", "Cary", "Research Triangle Park", "Chapel Hill", "Morrisville",
        "Apex", "Holly Springs", "Wake Forest", "Garner", "Knightdale", "Carrboro",
        "Fuquay-Varina", "RTP",
    ],
    "Salt Lake City": [
        "Salt Lake City", "Lehi", "Draper", "Provo", "Sandy", "South Jordan", "West Jordan",
        "Midvale", "Murray", "West Valley City", "Cottonwood Heights", "Herriman",
        "American Fork", "Orem", "Pleasant Grove", "Saratoga Springs",
    ],
    "San Antonio": [
        "San Antonio", "Schertz", "Cibolo", "Universal City", "Live Oak", "Converse",
        "New Braunfels", "Boerne",
    ],
    "San Francisco Bay Area": [
        "San Francisco", "San Jose", "Palo Alto", "Mountain View", "Sunnyvale", "Santa Clara",
        "Menlo Park", "Redwood City", "Foster City", "San Mateo", "Oakland", "Berkeley", "SF",
        "Fremont", "Newark", "Union City", "Hayward", "San Leandro", "Alameda", "Emeryville",
        "Richmond", "Walnut Creek", "San Ramon", "Dublin", "Pleasanton", "Livermore",
        "Milpitas", "Cupertino", "Campbell", "Los Gatos", "Los Altos", "Belmont", "San Carlos",
        "Burlingame", "Millbrae", "South San Francisco", "Daly City", "Brisbane", "San Bruno",
        "San Rafael", "Novato",
    ],
    "Seattle": [
        "Seattle", "Bellevue", "Redmond", "Kirkland", "Bothell", "Woodinville", "Issaquah",
        "Sammamish", "Renton", "Kent", "Tukwila", "SeaTac", "Federal Way", "Tacoma", "Everett",
        "Lynnwood", "Mountlake Terrace", "Edmonds", "Mercer Island", "Mukilteo",
    ],
}

CITY_OPTIONS = list(METRO_AREAS)

METRO_STATES = {
    "Atlanta": {"GA"},
    "Austin": {"TX"},
    "Boston": {"MA"},
    "Charlotte": {"NC", "SC"},
    "Chicago": {"IL"},
    "Columbus": {"OH"},
    "Dallas–Fort Worth": {"TX"},
    "Denver–Boulder": {"CO"},
    "Detroit–Ann Arbor": {"MI"},
    "Houston": {"TX"},
    "Indianapolis": {"IN"},
    "Kansas City": {"KS", "MO"},
    "Los Angeles": {"CA"},
    "Louisville": {"IN", "KY"},
    "Miami–Fort Lauderdale": {"FL"},
    "Minneapolis–St. Paul": {"MN"},
    "Nashville": {"TN"},
    "New York City": {"CT", "NJ", "NY"},
    "Philadelphia": {"DE", "NJ", "PA"},
    "Phoenix": {"AZ"},
    "Pittsburgh": {"PA"},
    "Portland": {"OR", "WA"},
    "Raleigh–Durham": {"NC"},
    "Salt Lake City": {"UT"},
    "San Antonio": {"TX"},
    "San Francisco Bay Area": {"CA"},
    "Seattle": {"WA"},
}

US_STATES = {

    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",

    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",

    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",

    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",

    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",

    "DC",

}

STATE_NAMES = {'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD', 'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC', 'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC'}

def location_state(location):
    parts = re.split(r"[,;]", location)
    for part in reversed(parts[1:]):
        cleaned = part.strip().casefold()
        if cleaned in STATE_NAMES:
            return STATE_NAMES[cleaned]
        if cleaned.upper() in US_STATES:
            return cleaned.upper()
    return ""

METRO_CITY_STATES = {
    ("Charlotte", "fort mill"): "SC",
    ("Charlotte", "rock hill"): "SC",
    ("Louisville", "new albany"): "IN",
    ("Louisville", "jeffersonville"): "IN",
    ("Louisville", "clarksville"): "IN",
    ("Portland", "vancouver"): "WA",
    ("Portland", "camas"): "WA",
}


def matches_metro(location, metro):

    state = location_state(location)
    if state not in METRO_STATES[metro]:
        return False
    city = location.split(",")[0].strip().casefold()
    expected_state = METRO_CITY_STATES.get((metro, city))
    return (expected_state is None or state == expected_state) and any(
        city == alias.casefold() for alias in METRO_AREAS[metro]
    )


def company_key(name):
    key = re.sub(r"[^a-z0-9]", "", name.casefold())
    if key in {"lockheedmartincorp", "lockheedmartincorporation", "lockheedmartincorplockheed"}:
        return "lockheedmartin"
    return key

def numeric_job_ids(role, link=""):

    # Long numeric requisition IDs; four-digit years are excluded.

    return set(re.findall(r"(?<![A-Za-z0-9])\d{6,}(?![A-Za-z0-9])", f"{role} {link}"))





def is_us_location(location):
    if re.search(r"(?:,\s*|^)(?:Canada|UK|United Kingdom|Australia|India)(?:\s*$)", location, re.I):
        return False
    if re.search(r",\s*(?:ON|QC|BC|AB|MB|NB|NL|NS|NT|NU|PE|SK|YT)(?:\s*,\s*CA)?\s*$", location, re.I):
        return False

    if re.search(r"(?:^|,\s*|\s)(?:USA|United States)\b|(?:^|,\s*)US\s*$", location, re.IGNORECASE):

        return True

    return location_state(location) in US_STATES

SOFTWARE_TITLE = re.compile(
    r"\bsoftware[\s/-]+(?:engineer(?:ing)?|developer|development|intern(?:ship)?|"
    r"programmer|programming)\b"
    r"|\b(?:applications?|apps?|front[ -]?end|back[ -]?end|full[ -]?stack|"
    r"web|mobile|android|ios|gameplay|embedded|firmware|cloud applications?|"
    r"technology|it|python|java|javascript|net)\s+(?:developer|development)\b"
    r"|\b(?:front[ -]?end|back[ -]?end|full[ -]?stack|mobile|android|ios|"
    r"gameplay|firmware)\s+engineer(?:ing)?\b"
    r"|\b(?:swe[\s/-]+intern(?:ship)?|programmer[\s/-]+intern(?:ship)?)\b"
    r"|^developer\s+(?:intern(?:ship)?|co[ -]?op)\b"
    r"|\bengineering\s+(?:intern(?:ship)?\s*[-–:]\s*developer|developer\s+intern)\b"
    r"|\bengineering\s+intern(?:ship)?\s*[-–:]\s*software\b",
    re.IGNORECASE,
)


def software_title_matches(title):
    return bool(SOFTWARE_TITLE.search(title))


def graduate_only_listing(listing):

    degrees = listing.get("degrees") or []

    if not isinstance(degrees, list) or not degrees:

        return False

    # Hide only when every stated degree is a graduate degree.

    return all(

        isinstance(degree, str)

        and re.fullmatch(

            r"masters?(?:degree)?|ms|msc|phd|doctorate|doctoral(?:degree)?",

            re.sub(r"[^a-z]", "", degree.casefold()),

        ) is not None

        for degree in degrees

    )





