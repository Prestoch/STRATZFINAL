#!/usr/bin/env python3
"""
Test different query approaches to find one that works without admin access
"""

import cloudscraper
import json

API_KEY = "YOUR_API_KEY_HERE"

def test_single_match_query():
    """Test querying a single match (not batch)"""
    print("\n" + "="*60)
    print("TEST 1: Single match query")
    print("="*60)
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    # Query ONE match at a time
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
    
    try:
        response = scraper.post(
            "https://api.stratz.com/graphql",
            json={"query": query, "variables": {"id": 6449050893}},
            headers=headers,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Errors: {json.dumps(data['errors'], indent=2)}")
            return False
        elif "data" in data and "match" in data["data"]:
            match = data["data"]["match"]
            print("✅ SUCCESS!")
            print(f"Match ID: {match['id']}")
            print(f"League ID: {match.get('leagueId')}")
            if match.get('league'):
                print(f"League Name: {match['league'].get('displayName')}")
                print(f"League Tier: {match['league'].get('tier')}")
            return True
        else:
            print(f"Unexpected: {json.dumps(data, indent=2)}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_simple_match_query():
    """Test with minimal fields"""
    print("\n" + "="*60)
    print("TEST 2: Minimal fields query")
    print("="*60)
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    # Minimal query
    query = """
    query GetMatch($id: Long!) {
        match(id: $id) {
            id
            leagueId
        }
    }
    """
    
    try:
        response = scraper.post(
            "https://api.stratz.com/graphql",
            json={"query": query, "variables": {"id": 6449050893}},
            headers=headers,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Errors: {json.dumps(data['errors'], indent=2)}")
            return False
        elif "data" in data:
            print("✅ SUCCESS!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"Unexpected: {json.dumps(data, indent=2)}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_league_query():
    """Test querying league by ID instead"""
    print("\n" + "="*60)
    print("TEST 3: Query league by ID")
    print("="*60)
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    # Query league directly
    query = """
    query GetLeague($id: Int!) {
        league(id: $id) {
            id
            displayName
            tier
        }
    }
    """
    
    try:
        response = scraper.post(
            "https://api.stratz.com/graphql",
            json={"query": query, "variables": {"id": 14268}},
            headers=headers,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Errors: {json.dumps(data['errors'], indent=2)}")
            return False
        elif "data" in data:
            print("✅ SUCCESS!")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"Unexpected: {json.dumps(data, indent=2)}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    import sys
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set your API key!")
        sys.exit(1)
    
    print("Testing different query approaches...")
    
    tests = [
        test_single_match_query,
        test_simple_match_query,
        test_league_query
    ]
    
    results = []
    for test in tests:
        try:
            success = test()
            results.append((test.__name__, success))
        except Exception as e:
            print(f"Test crashed: {e}")
            results.append((test.__name__, False))
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    if any(s for _, s in results):
        print("\n✅ Found a working query! Will update the main script.")
    else:
        print("\n❌ No queries worked. May need different approach.")


if __name__ == "__main__":
    main()
