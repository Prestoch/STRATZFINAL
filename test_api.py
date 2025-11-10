#!/usr/bin/env python3
"""
Quick test script to verify Stratz API keys work correctly
before processing all 96,507 matches.

Note: This script makes very few API calls, so rate limits won't be an issue.
Stratz limits per key: 20/sec, 250/min, 2000/hour, 10000/day
"""

import json
import requests
import sys

# Add your API keys here (same as in add_league_tier.py)
API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2", 
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

STRATZ_API_URL = "https://api.stratz.com/graphql"

def test_api_key(api_key: str, match_ids: list) -> bool:
    """Test a single API key with a few match IDs"""
    
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
        "matchIds": [int(mid) for mid in match_ids]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            STRATZ_API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 401:
            print(f"  ❌ FAILED - Invalid API key (401 Unauthorized)")
            return False
        
        if response.status_code == 429:
            print(f"  ⚠️  Rate limited (429) - but key is valid")
            return True
            
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"  ❌ FAILED - GraphQL errors: {data['errors']}")
            return False
        
        if "data" in data and "matches" in data["data"]:
            matches = data["data"]["matches"]
            valid_matches = [m for m in matches if m is not None]
            print(f"  ✓ SUCCESS - Retrieved data for {len(valid_matches)} matches")
            
            # Show sample data
            if valid_matches:
                sample = valid_matches[0]
                print(f"    Sample: Match {sample['id']}")
                if sample.get('league'):
                    print(f"      League: {sample['league'].get('displayName')}")
                    print(f"      Tier: {sample['league'].get('tier')}")
                else:
                    print(f"      League: None")
            return True
        else:
            print(f"  ❌ FAILED - No match data in response")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ FAILED - Request error: {e}")
        return False


def main():
    """Test all API keys"""
    
    # Check if API keys are set
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("❌ ERROR: Please add your Stratz API keys to this script!")
        print("Edit the API_KEYS list at the top of test_api.py")
        sys.exit(1)
    
    # Load a few match IDs from the dataset
    print("Loading sample match IDs from dataset...")
    try:
        with open("stratz_clean_96507.json", 'r') as f:
            # Read just enough to get some match IDs
            sample = f.read(5000)
            # Parse a bit of the JSON to get match IDs
            data = json.loads(sample + '}}')
            match_ids = list(data.keys())[:5]
        print(f"Testing with match IDs: {match_ids}\n")
    except Exception as e:
        print(f"Error loading match IDs: {e}")
        print("Using default test match IDs...")
        match_ids = ["6449050893", "6449058478", "6449061020"]
    
    # Test each API key
    print("Testing API keys...\n")
    valid_keys = 0
    
    for i, api_key in enumerate(API_KEYS, 1):
        # Mask the key for display
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"API Key {i}/{len(API_KEYS)} ({masked_key}):")
        
        if test_api_key(api_key, match_ids):
            valid_keys += 1
        print()
    
    # Summary
    print("=" * 60)
    print(f"RESULTS: {valid_keys}/{len(API_KEYS)} API keys are valid and working")
    print("=" * 60)
    
    # Show rate limit capacity
    if valid_keys > 0:
        print(f"\n📊 Combined Rate Limit Capacity ({valid_keys} keys):")
        print(f"   {valid_keys * 20} calls/second")
        print(f"   {valid_keys * 250} calls/minute")
        print(f"   {valid_keys * 2000} calls/hour")
        print(f"   {valid_keys * 10000} calls/day")
    
    if valid_keys == 0:
        print("\n❌ No valid API keys found. Please check your keys and try again.")
        sys.exit(1)
    elif valid_keys < len(API_KEYS):
        print(f"\n⚠️  {len(API_KEYS) - valid_keys} API key(s) failed.")
        print("You can proceed, but consider replacing the failed keys for better performance.")
    else:
        print("\n✓ All API keys are working! You're ready to run add_league_tier.py")
    
    print(f"\nNext step: python3 add_league_tier.py")


if __name__ == "__main__":
    main()
