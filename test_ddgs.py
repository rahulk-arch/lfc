from gemini_keyword import generate_queries
from ddgs_search import search_web

queries = generate_queries(
    "Education NGO",
    "New Delhi"
)

results = search_web(queries)

print(f"\nTotal results: {len(results)}")