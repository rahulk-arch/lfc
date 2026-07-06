from serperai import search_web
import time

test_queries = [
    "Education NGO Delhi",
    "NGO for Education Delhi",
]

start = time.time()
results = search_web(test_queries, category="Education", location="Delhi")
print(f"\nGot {len(results)} results in {time.time()-start:.1f} seconds\n")

for i, row in enumerate(results, start=1):
    print(f"{i}. {row['Title']}")
    print(f"   URL: {row['URL']}")
    print(f"   Type: {row['Result Type']}")
    print()