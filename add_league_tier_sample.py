#!/usr/bin/env python3
"""
Sample script to test the league/tier fetching on just 100 matches
Run this first to verify everything works before processing all 96k matches!
"""

import json
import time
import requests
from typing import Dict, List
from collections import deque

# Stratz GraphQL endpoint
STRATZ_API_URL = "https://api.stratz.com/graphql"

# API keys (you'll need to provide these)
API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

# Process only first N matches for testing
SAMPLE_SIZE = 100


class StratzAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = deque(api_keys)
        self.current_key_index = 0
        self.request_count = 0
        self.rate_limit_per_minute = 100
        self.last_reset_time = time.time()
        
    def rotate_key(self):
        """Rotate to the next API key"""
        self.api_keys.rotate(-1)
        print(f"  → Rotated to next API key")
        
    def get_current_key(self) -> str:
        """Get the current API key"""
        return self.api_keys[0]
    
    def fetch_match_league_data(self, match_ids: List[str]) -> Dict:
        """Fetch league/tier data for a batch of match IDs"""
        
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
            "Authorization": f"Bearer {self.get_current_key()}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                STRATZ_API_URL,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            self.request_count += 1
            
            if response.status_code == 429:
                print("  Rate limited, rotating API key...")
                self.rotate_key()
                time.sleep(2)
                return self.fetch_match_league_data(match_ids)
            
            if response.status_code == 401:
                print("  API key invalid, rotating...")
                self.rotate_key()
                return self.fetch_match_league_data(match_ids)
            
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"  GraphQL errors: {data['errors']}")
                return {}
            
            result = {}
            if "data" in data and "matches" in data["data"]:
                for match in data["data"]["matches"]:
                    if match:
                        match_id = str(match["id"])
                        result[match_id] = {
                            "leagueId": match.get("leagueId"),
                            "leagueName": match.get("league", {}).get("displayName") if match.get("league") else None,
                            "leagueTier": match.get("league", {}).get("tier") if match.get("league") else None
                        }
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            time.sleep(5)
            return {}


def main():
    """Main execution for sample processing"""
    import sys
    
    print("=" * 70)
    print("SAMPLE TEST - Processing first 100 matches")
    print("=" * 70)
    
    # Check if API keys are provided
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys to the script!")
        print("Edit the API_KEYS list at the top of this file.")
        sys.exit(1)
    
    # Initialize API client
    api_client = StratzAPIClient(API_KEYS)
    
    # Load matches
    print("\n1. Loading matches...")
    with open("stratz_clean_96507.json", 'r') as f:
        all_matches = json.load(f)
    
    # Get sample
    all_match_ids = list(all_matches.keys())
    sample_ids = all_match_ids[:SAMPLE_SIZE]
    sample_matches = {mid: all_matches[mid] for mid in sample_ids}
    
    print(f"   Loaded {len(sample_matches)} matches for testing")
    
    # Process in batches
    print(f"\n2. Fetching league/tier data...")
    batch_size = 50
    added_data = 0
    
    for i in range(0, len(sample_ids), batch_size):
        batch_ids = sample_ids[i:i+batch_size]
        print(f"   Batch {i//batch_size + 1}/{(len(sample_ids) + batch_size - 1)//batch_size}...", end=" ")
        
        league_data = api_client.fetch_match_league_data(batch_ids)
        
        for match_id in batch_ids:
            if match_id in league_data:
                sample_matches[match_id].update(league_data[match_id])
                if league_data[match_id].get("leagueTier"):
                    added_data += 1
            else:
                sample_matches[match_id].update({
                    "leagueId": None,
                    "leagueName": None,
                    "leagueTier": None
                })
        
        print(f"✓ ({added_data} with tier data so far)")
        time.sleep(0.5)
    
    # Save sample output
    print(f"\n3. Saving sample output...")
    output_file = "stratz_sample_with_tiers.json"
    with open(output_file, 'w') as f:
        json.dump(sample_matches, f, indent=2)
    
    # Show statistics
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Processed: {len(sample_matches)} matches")
    print(f"With tier data: {added_data} matches ({100*added_data/len(sample_matches):.1f}%)")
    print(f"Output saved to: {output_file}")
    
    # Show a few examples
    print("\nSample data preview:")
    print("-" * 70)
    count = 0
    for match_id, data in sample_matches.items():
        if data.get("leagueTier") and count < 3:
            print(f"Match {match_id}:")
            print(f"  League: {data.get('leagueName', 'N/A')}")
            print(f"  Tier: {data.get('leagueTier', 'N/A')}")
            count += 1
    
    if added_data == 0:
        print("\n⚠️  No tier data found. This might mean:")
        print("   - These matches don't have associated league data")
        print("   - Try different match IDs from your dataset")
    else:
        print("\n✓ SUCCESS! The API is working correctly.")
        print("  You can now run the full script: python3 add_league_tier.py")


if __name__ == "__main__":
    main()
