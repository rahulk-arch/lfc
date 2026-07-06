from automation_v2 import run_automation

results = run_automation(
    category="children",
    location="Delhi",
    search_entity="NGO"
)

print("\nFinal Results:")
print(results)