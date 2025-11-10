#!/usr/bin/env python3
import cloudscraper
import json

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJTdWJqZWN0IjoiY2UxZGYzZjktMzg3Ny00ZTNhLWI1M2UtNzQzOWE5YTI4ODA3IiwiU3RlYW1JZCI6IjEwMDA3MDcxNDMiLCJBUElVc2VyIjoidHJ1ZSIsIm5iZiI6MTc2Mjc0NDgyMSwiZXhwIjoxNzk0MjgwODIxLCJpYXQiOjE3NjI3NDQ4MjEsImlzcyI6Imh0dHBzOi8vYXBpLnN0cmF0ei5jb20ifQ.JNRKtNhi-McyaW-J7MQGJcMeGxCYKCeY8h619cZTO-4"

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False})

headers = {
    "authorization": f"bearer {API_KEY}",
    "content-type": "application/json",
    "origin": "https://stratz.com",
    "referer": "https://stratz.com/",
}

# Test single match
query = """
query GetMatch($id: Long!) {
    match(id: $id) {
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

response = scraper.post(
    "https://api.stratz.com/graphql",
    json={"query": query, "variables": {"id": 6449050893}},
    headers=headers,
    timeout=15
)

print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
