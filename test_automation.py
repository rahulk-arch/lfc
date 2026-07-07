from automation_v2 import run_automation

results = run_automation(
    category="Children",
    location="Bangalore",
    search_entity="NGO",
    target_count=20
)

print(results)