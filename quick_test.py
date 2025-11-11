#!/usr/bin/env python3
"""
Quick test with the corrected headers from curl command
"""

import requests
import json

# Your API key
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJTdWJqZWN0IjoiY2UxZGYzZjktMzg3Ny00ZTNhLWI1M2UtNzQzOWE5YTI4ODA3IiwiU3RlYW1JZCI6IjEwMDA3MDcxNDMiLCJBUElVc2VyIjoidHJ1ZSIsIm5iZiI6MTc2Mjc0NDgyMSwiZXhwIjoxNzk0MjgwODIxLCJpYXQiOjE3NjI3NDQ4MjEsImlzcyI6Imh0dHBzOi8vYXBpLnN0cmF0ei5jb20ifQ.JNRKtNhi-McyaW-J7MQGJcMeGxCYKCeY8h619cZTO-4"

# Test match IDs
test_ids = ["6449050893", "6449058478", "6449061020"]

# Corrected headers based on working curl command
headers = {
    "authorization": f"bearer {API_KEY}",
    "content-type": "application/json",
    "origin": "https://stratz.com",
    "referer": "https://stratz.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

query = """
query GetMatchLeagues($matchIds: [Long!]!) {
    matches(ids: $matchIds) {
        id
        leagueId
        league {
            id
            displayName
            tier
        }
    }
}
"""

variables = {
    "matchIds": [int(mid) for mid in test_ids]
}

print("Testing Stratz API with corrected headers...")
print("=" * 60)

try:
    response = requests.post(
        "https://api.stratz.com/graphql",
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        
        if "errors" in data:
            print("❌ GraphQL Errors:")
            print(json.dumps(data["errors"], indent=2))
        elif "data" in data and "matches" in data["data"]:
            print("✅ SUCCESS! Retrieved data:")
            print()
            for match in data["data"]["matches"]:
                if match:
                    print(f"Match ID: {match['id']}")
                    print(f"  League ID: {match.get('leagueId')}")
                    if match.get('league'):
                        print(f"  League Name: {match['league'].get('displayName')}")
                        print(f"  League Tier: {match['league'].get('tier')}")
                    else:
                        print(f"  League: None")
                    print()
        else:
            print("Unexpected response format:")
            print(json.dumps(data, indent=2))
    else:
        print(f"❌ HTTP Error {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ Error: {e}")

print("=" * 60)
