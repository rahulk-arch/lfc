from urllib.parse import urlparse
from knowledge_generator import generate_knowledge
from query_builder import build_queries
from serperai import search_web
from website_validator_v2 import validate_websites
from test_v2 import extract_organizations


def strip_www(netloc: str) -> str:
    netloc = netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def dedup_organizations(new_orgs, seen_domains):
    unique = []
    for org in new_orgs:
        domain = strip_www(urlparse(org.get("Website", "")).netloc)
        if domain and domain not in seen_domains:
            seen_domains.add(domain)
            unique.append(org)
    return unique


def run_automation(category, location, search_entity, target_count=100,
                    max_total_queries=250, batch_size=10, progress_callback=None, stop_event=None):
    print("Generating knowledge graph...")

    if progress_callback:
        progress_callback(tier="Knowledge Graph", total_orgs=0, organizations=[], done=False)

    MAX_QUERIES_PER_TIER = {
        "tier1": 15,
        "tier2": 60,
        "tier3": 50,
        "tier4": 40,
        "tier5": 15,
    }

    graph = generate_knowledge(category, location)
    print("\n===== KNOWLEDGE GRAPH =====")
    print(graph)
    category_signals = list(set(
        graph.get("keywords", [])
        + graph.get("activities", [])
        + graph.get("beneficiaries", [])
        + graph.get("synonyms", [])
    ))
    query_tiers = build_queries(graph, category, location, search_entity)
    print("\n===== GENERATED QUERIES =====")
    for tier, queries in query_tiers.items():
        print(f"\n{tier}:")
        for q in queries[:5]:      # print first 5 only
            print(" ", q)

    all_organizations = []
    seen_domains = set()
    total_queries_run = 0

    for tier_name, queries in query_tiers.items():
        limit = MAX_QUERIES_PER_TIER.get(tier_name, len(queries))
        queries = queries[:limit]

        for batch_start in range(0, len(queries), batch_size):
            # Stop button was pressed — return whatever we have right now
            if stop_event is not None and stop_event.is_set():
                if progress_callback:
                    progress_callback(tier=tier_name, total_orgs=len(all_organizations),
                                       organizations=all_organizations, done=True)
                return all_organizations

            remaining_budget = max_total_queries - total_queries_run
            if remaining_budget <= 0:
                if progress_callback:
                    progress_callback(tier=tier_name, total_orgs=len(all_organizations),
                                       organizations=all_organizations, done=True)
                return all_organizations
            
            batch = queries[batch_start: batch_start + batch_size][:remaining_budget]
            if not batch:
                break

            total_queries_run += len(batch)

            search_results = search_web(batch, category, location)

            def rank_candidate(item):
                score = 0
                if item["Result Type"] == "Official Website":
                    score += 3
                elif item["Result Type"] == "Government":
                    score += 2
                score += item.get("Location Hint Score", 0) * 2
                return score

            search_results.sort(key=rank_candidate, reverse=True)
            top_candidates = search_results[:40]
            
            validated = validate_websites(top_candidates, category_signals=category_signals, location=location)
            organizations = extract_organizations(validated)
            organizations = dedup_organizations(organizations, seen_domains)

            all_organizations.extend(organizations)

            if progress_callback:
                progress_callback(
                    tier=tier_name,
                    total_orgs=len(all_organizations),
                    organizations=all_organizations,
                    done=False
                )

            if len(all_organizations) >= target_count:
                if progress_callback:
                    progress_callback(
                        tier=tier_name, 
                        total_orgs=len(all_organizations),
                        organizations=all_organizations,
                        done=True)
                return all_organizations

    if progress_callback:
        progress_callback(tier="Finished", total_orgs=len(all_organizations),
                           organizations=all_organizations, done=True)

    return all_organizations