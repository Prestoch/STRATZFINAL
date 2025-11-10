#!/usr/bin/env python3
"""
Test if cloudscraper can bypass Cloudflare protection

Install: pip install cloudscraper
"""

import cloudscraper
import json

API_KEY = "YOUR_API_KEY_HERE"

def test_cloudscraper():
    print("Testing Cloudflare bypass with cloudscraper...")
    print("=" * 60)
    
    # Create scraper
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'darwin',
            'mobile': False
        }
    )
    
    # Test match IDs
    test_ids = ["6449050893", "6449058478", "6449061020"]
    
    # Headers matching working curl
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
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
    
    try:
        response = scraper.post(
            "https://api.stratz.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}\n")
        
        if response.status_code == 200:
            data = response.json()
            
            if "errors" in data:
                print("❌ GraphQL Errors:")
                print(json.dumps(data["errors"], indent=2))
            elif "data" in data and "matches" in data["data"]:
                print("✅ SUCCESS! Cloudflare bypassed!")
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
                
                print("✅ Ready to process all 96,507 matches!")
            else:
                print("Unexpected response:")
                print(json.dumps(data, indent=2))
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set your API key at the top of this script!")
        sys.exit(1)
    
    test_cloudscraper()
