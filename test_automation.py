from automation_parallel import run_parallel_pipeline

results = run_parallel_pipeline(
    category="Children",
    location="Bangalore",
    search_entity="NGO",
    target_count=10
)

print(results)