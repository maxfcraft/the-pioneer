"""
Exhaustive search term matrix.
Cities x variations = 300+ unique queries across Google, Bing, DDG, and Facebook.
"""

CITIES = [
    {"city": "Mobile",       "state": "AL", "high_schools": ["Murphy", "Davidson", "McGill-Toolen", "St. Paul's", "Vigor", "Blount", "Williamson"]},
    {"city": "Huntsville",   "state": "AL", "high_schools": ["Grissom", "Huntsville High", "Johnson", "Columbia", "Bob Jones", "James Clemens", "Buckhorn"]},
    {"city": "Birmingham",   "state": "AL", "high_schools": ["Hoover", "Spain Park", "Vestavia Hills", "Mountain Brook", "Oak Mountain", "Hewitt-Trussville", "Chelsea", "Pelham"]},
    {"city": "Montgomery",   "state": "AL", "high_schools": ["Prattville", "Wetumpka", "Stanhope Elmore", "Jefferson Davis", "Lanier", "Carver"]},
    {"city": "Tuscaloosa",   "state": "AL", "high_schools": ["Tuscaloosa County", "Central", "Northridge", "American Christian", "Hillcrest"]},
    {"city": "Dothan",       "state": "AL", "high_schools": ["Dothan High", "Northview", "Rehobeth", "Houston Academy", "Carroll"]},
    {"city": "Decatur",      "state": "AL", "high_schools": ["Decatur High", "Austin", "Hartselle", "West Morgan"]},
    {"city": "Gadsden",      "state": "AL", "high_schools": ["Gadsden City", "Etowah", "Sardis", "Westbrook Christian"]},
    {"city": "Auburn",       "state": "AL", "high_schools": ["Auburn High", "Opelika High", "Lee-Scott"]},
    {"city": "Anniston",     "state": "AL", "high_schools": ["Anniston High", "Alexandria", "Jacksonville"]},
    {"city": "Florence",     "state": "AL", "high_schools": ["Florence High", "Coffee High", "Brooks"]},
    {"city": "Phenix City",  "state": "AL", "high_schools": ["Central-Phenix City", "Glenwood"]},
    {"city": "Pensacola",    "state": "FL", "high_schools": ["Pensacola High", "Escambia", "Pine Forest", "Catholic High", "West Florida", "Tate"]},
    {"city": "Atlanta",      "state": "GA", "high_schools": ["Alpharetta", "Milton", "Roswell", "Johns Creek", "Walton", "Lassiter", "Pope", "Blessed Trinity"]},
    {"city": "Nashville",    "state": "TN", "high_schools": ["Brentwood", "Franklin", "Ravenwood", "Centennial"]},
    {"city": "Memphis",      "state": "TN", "high_schools": ["Houston", "Collierville", "Germantown", "White Station"]},
    {"city": "Columbus",     "state": "GA", "high_schools": ["Brookstone", "Northside", "Hardaway", "Carver"]},
]

# All the ways someone might name an Auburn group
AUBURN_VARIATIONS = [
    "Auburn University",
    "Auburn Univ",
    "AU",
    "War Eagle",
    "Auburn Tigers",
    "Auburn freshman",
    "Auburn 2029",
    "Auburn 2028",
    "Auburn 2030",
    "Camp War Eagle",
    "Auburn incoming",
    "Auburn parents",
    "Auburn moms",
    "Auburn families",
    "Auburn orientation",
    "Auburn University parents",
    "Auburn University moms",
    "Auburn University class of 2029",
    "Auburn class 2029",
    "Auburn University families",
    "Auburn University freshman",
    "Auburn University students",
    "Auburn University alumni",
    "Roll Tide rival",  # Sometimes rival fan groups mention Auburn
]

GROUP_TYPE_SUFFIXES = [
    "group",
    "parents",
    "moms",
    "families",
    "students",
    "freshman",
    "class of 2029",
    "2029",
    "community",
    "support group",
    "network",
]

def build_fb_search_terms() -> list[dict]:
    """Build full matrix of (city, search_term) pairs for Facebook search."""
    terms = []

    # City-specific terms
    for city_data in CITIES:
        city = city_data["city"]
        state = city_data["state"]
        for variation in AUBURN_VARIATIONS[:10]:  # Top 10 per city = 180 city terms
            terms.append({
                "city": city,
                "state": state,
                "term": f"{variation} {city}",
                "high_schools": city_data["high_schools"],
            })
        # Also just city name with Auburn
        terms.append({"city": city, "state": state, "term": f"Auburn {city} {state}", "high_schools": city_data["high_schools"]})

    # Global Auburn terms (no city filter)
    for variation in AUBURN_VARIATIONS:
        for suffix in GROUP_TYPE_SUFFIXES:
            terms.append({
                "city": "Auburn",
                "state": "AL",
                "term": f"{variation} {suffix}",
                "high_schools": [],
            })

    return terms


def build_google_dork_queries() -> list[dict]:
    """Build Google/Bing dork queries that surface hidden FB groups."""
    queries = []

    # Core dorks
    base_dorks = [
        'site:facebook.com/groups "Auburn University"',
        'site:facebook.com/groups "War Eagle" parents',
        'site:facebook.com/groups "Auburn" freshman parents',
        'site:facebook.com/groups "Camp War Eagle"',
        'site:facebook.com/groups "Auburn University" moms',
        'site:facebook.com/groups "Auburn University" class 2029',
        'site:facebook.com/groups "Auburn" incoming freshmen',
    ]

    # City-specific dorks
    for city_data in CITIES:
        city = city_data["city"]
        state = city_data["state"]
        queries.append({
            "query": f'site:facebook.com/groups "Auburn" "{city}"',
            "city": city,
            "state": state,
            "platform": "facebook",
        })
        queries.append({
            "query": f'site:facebook.com/groups "War Eagle" "{city}"',
            "city": city,
            "state": state,
            "platform": "facebook",
        })

    for dork in base_dorks:
        queries.append({"query": dork, "city": "Auburn", "state": "AL", "platform": "facebook"})

    return queries


REDDIT_TARGETS = [
    # Direct Auburn subs
    {"sub": "AuburnUniversity", "type": "direct"},
    {"sub": "auburn", "type": "direct"},
    {"sub": "WarEagle", "type": "direct"},
    # Alabama city subs
    {"sub": "Birmingham", "type": "city"},
    {"sub": "Huntsville", "type": "city"},
    {"sub": "MobileAL", "type": "city"},
    {"sub": "Montgomery", "type": "city"},
    {"sub": "Tuscaloosa", "type": "city"},
    {"sub": "Alabama", "type": "state"},
    # Neighboring state subs
    {"sub": "Atlanta", "type": "city"},
    {"sub": "Georgia", "type": "state"},
    {"sub": "Pensacola", "type": "city"},
    {"sub": "florida", "type": "state"},
    {"sub": "nashville", "type": "city"},
    {"sub": "Tennessee", "type": "state"},
    # General college/parent subs
    {"sub": "college", "type": "general"},
    {"sub": "ApplyingToCollege", "type": "general"},
    {"sub": "CollegeParents", "type": "general"},
    {"sub": "newparents", "type": "general"},
]
