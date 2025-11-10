#!/usr/bin/env python3
"""
Sample script to test the league/tier fetching on just 100 matches
Run this first to verify everything works before processing all 96k matches!

Respects Stratz rate limits:
- 20 calls/second per key
- 250 calls/minute per key
- 2,000 calls/hour per key
- 10,000 calls/day per key
"""

import json
import time
import requests
from typing import Dict, List, Optional
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

# Stratz API rate limits per key (set at 80% of actual limits for safety)
# Actual Stratz limits: 20/sec, 250/min, 2000/hour, 10000/day
RATE_LIMITS = {
    'second': 15,
    'minute': 200,
    'hour': 1600,
    'day': 8000
}


class RateLimitTracker:
    """Tracks API calls for a single key across different time windows"""
    
    def __init__(self, key_id: int):
        self.key_id = key_id
        self.calls_second = []
        self.calls_minute = []
        self.calls_hour = []
        self.calls_day = []
        
    def record_call(self):
        """Record a new API call"""
        now = time.time()
        self.calls_second.append(now)
        self.calls_minute.append(now)
        self.calls_hour.append(now)
        self.calls_day.append(now)
        
    def clean_old_calls(self):
        """Remove calls outside the tracking windows"""
        now = time.time()
        self.calls_second = [t for t in self.calls_second if now - t < 1]
        self.calls_minute = [t for t in self.calls_minute if now - t < 60]
        self.calls_hour = [t for t in self.calls_hour if now - t < 3600]
        self.calls_day = [t for t in self.calls_day if now - t < 86400]
        
    def can_make_call(self) -> bool:
        """Check if we can make another call without exceeding limits"""
        self.clean_old_calls()
        return (
            len(self.calls_second) < RATE_LIMITS['second'] and
            len(self.calls_minute) < RATE_LIMITS['minute'] and
            len(self.calls_hour) < RATE_LIMITS['hour'] and
            len(self.calls_day) < RATE_LIMITS['day']
        )
    
    def time_until_available(self) -> float:
        """Calculate seconds until next call is available"""
        self.clean_old_calls()
        now = time.time()
        wait_times = []
        
        if len(self.calls_second) >= RATE_LIMITS['second']:
            wait_times.append(1 - (now - self.calls_second[0]))
        if len(self.calls_minute) >= RATE_LIMITS['minute']:
            wait_times.append(60 - (now - self.calls_minute[0]))
        if len(self.calls_hour) >= RATE_LIMITS['hour']:
            wait_times.append(3600 - (now - self.calls_hour[0]))
        if len(self.calls_day) >= RATE_LIMITS['day']:
            wait_times.append(86400 - (now - self.calls_day[0]))
            
        return max(wait_times) if wait_times else 0


class StratzAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.trackers = [RateLimitTracker(i) for i in range(len(api_keys))]
        self.current_key_index = 0
        self.total_calls = 0
        
    def get_available_key_index(self) -> Optional[int]:
        """Find an API key that can make a call right now"""
        if self.trackers[self.current_key_index].can_make_call():
            return self.current_key_index
        
        for i in range(len(self.api_keys)):
            if self.trackers[i].can_make_call():
                return i
                
        return None
    
    def wait_for_available_key(self) -> int:
        """Wait until a key is available and return its index"""
        key_idx = self.get_available_key_index()
        if key_idx is not None:
            self.current_key_index = key_idx
            return key_idx
        
        # Find minimum wait time
        wait_times = [tracker.time_until_available() for tracker in self.trackers]
        min_wait = min(wait_times)
        
        if min_wait > 0:
            print(f"  ⏳ Rate limit reached, waiting {min_wait:.1f}s...")
            time.sleep(min_wait + 0.1)
        
        return self.wait_for_available_key()
    
    def fetch_match_league_data(self, match_ids: List[str]) -> Dict:
        """Fetch league/tier data for a batch of match IDs"""
        
        key_idx = self.wait_for_available_key()
        
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
            "authorization": f"bearer {self.api_keys[key_idx]}",
            "content-type": "application/json",
            "origin": "https://stratz.com",
            "referer": "https://stratz.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        }
        
        try:
            response = requests.post(
                STRATZ_API_URL,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            self.trackers[key_idx].record_call()
            self.total_calls += 1
            
            if response.status_code == 429:
                print(f"  ⚠️  Rate limited, rotating...")
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                time.sleep(2)
                return self.fetch_match_league_data(match_ids)
            
            if response.status_code == 401:
                print(f"  ❌ Invalid key, trying next...")
                self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
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
        print("Edit the API_KEYS list at the top of this file.\n")
        sys.exit(1)
    
    # Initialize API client
    print(f"\nRate limits per key: {RATE_LIMITS['second']}/sec, {RATE_LIMITS['minute']}/min")
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
    print(f"Total API calls: {api_client.total_calls}")
    print(f"Output saved to: {output_file}")
    
    # Show a few examples
    print("\n📋 Sample data preview:")
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
        print("\n✅ SUCCESS! The API is working correctly.")
        print("   You can now run the full script: python3 add_league_tier.py")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
