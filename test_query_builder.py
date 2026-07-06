from knowledge_generator import generate_knowledge
from query_builder import build_queries

graph = generate_knowledge(
    "Education NGO",
    "Delhi"
)

queries = build_queries(
    graph,
    "Delhi"
)

print(len(queries))

for q in queries[:30]:
    print(q)