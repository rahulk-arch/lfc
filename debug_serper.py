import os
import requests

print("Environment key:", os.environ.get("SERPER_API_KEY"))

API_KEY = os.environ.get("SERPER_API_KEY")

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "q": "NGO"
}

response = requests.post(
    "https://google.serper.dev/search",
    headers=headers,
    json=payload
)

print("Status:", response.status_code)
print("Response:", response.text)