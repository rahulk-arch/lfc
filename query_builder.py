def build_queries(graph, category, location, search_entity):

    activities = graph.get("activities", [])
    beneficiaries = graph.get("beneficiaries", [])
    synonyms = graph.get("synonyms", [])
    locations = graph.get("location_aliases", [location])


    tier1 = []
    tier2 = []
    tier3 = []
    tier4 = []
    tier5 = []


    tier1.append(f"{category} {search_entity} {location}")
    tier1.append(f"{search_entity} for {category} {location}")
    tier1.append(f"{category} {search_entity} in {location}")
    tier1.append(f"{category} {search_entity} near {location}")
    tier1.append(f"{search_entity} {category} {location}")
    tier1.append(f"{category} focused {search_entity} {location}")
    tier1.append(f"{search_entity} working on {category} {location}")
    tier1.append(f"{search_entity} for {category} in {location}")
    tier1.append(f"{category} {search_entity} based in {location}")
    tier1.append(f"{search_entity} serving {category} in {location}")
    tier1.append(f"leading {category} {search_entity} {location}")
    tier1.append(f"local {category} {search_entity} {location}")
    tier1.append(f"{search_entity} dedicated to {category} {location}")
    tier1.append(f"{category} {search_entity} organization {location}")
    tier1.append(f"registered {category} {search_entity} {location}")


    for activity in activities:

        tier2.append(f"{activity} {search_entity} {location}")
        tier2.append(f"{search_entity} for {activity} {location}")


    for beneficiary in beneficiaries:

        tier3.append(f"{search_entity} for {beneficiary} {location}")
        tier3.append(f"{beneficiary} {search_entity} {location}")


    for synonym in synonyms:

        tier4.append(f"{synonym} {search_entity} {location}")
        tier4.append(f"{synonym} {location}")


    for locality in locations:

        tier5.append(f"{category} {search_entity} {locality}")
    


    return {
        "tier1": tier1,
        "tier2": tier2,
        "tier3": tier3,
        "tier4": tier4,
        "tier5": tier5
    }