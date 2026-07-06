from ddgs_search_v2 import search_web

test_queries = [
    "Education NGO Delhi",
    "NGO for Education Delhi",
    "Teacher Training NGO Delhi",
]

results = search_web(test_queries, category="Education", location="Delhi")
print(f"\nGot {len(results)} results")