#!/usr/bin/env python3
"""
Script to fetch league/tier data for Dota 2 pro matches from Stratz API
and add it to the existing dataset.

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
from datetime import datetime, timedelta

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
    
    def get_stats(self) -> Dict:
        """Get current usage stats"""
        self.clean_old_calls()
        return {
            'second': len(self.calls_second),
            'minute': len(self.calls_minute),
            'hour': len(self.calls_hour),
            'day': len(self.calls_day)
        }


class StratzAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.trackers = [RateLimitTracker(i) for i in range(len(api_keys))]
        self.current_key_index = 0
        self.total_calls = 0
        self.failed_calls = 0
        self.start_time = time.time()
        
    def get_available_key_index(self) -> Optional[int]:
        """Find an API key that can make a call right now"""
        # Try current key first
        if self.trackers[self.current_key_index].can_make_call():
            return self.current_key_index
        
        # Try other keys
        for i in range(len(self.api_keys)):
            if self.trackers[i].can_make_call():
                return i
                
        return None
    
    def wait_for_available_key(self) -> int:
        """Wait until a key is available and return its index"""
        while True:
            key_idx = self.get_available_key_index()
            if key_idx is not None:
                self.current_key_index = key_idx
                return key_idx
            
            # Find minimum wait time across all keys
            wait_times = [tracker.time_until_available() for tracker in self.trackers]
            min_wait = min(wait_times)
            
            if min_wait > 0:
                print(f"  ⏳ Rate limit reached on all keys. Waiting {min_wait:.1f}s...")
                time.sleep(min_wait + 0.1)  # Small buffer
            else:
                time.sleep(0.1)
    
    def get_current_key(self) -> str:
        """Get the current API key"""
        return self.api_keys[self.current_key_index]
    
    def print_stats(self):
        """Print current rate limit statistics"""
        elapsed = time.time() - self.start_time
        print(f"\n📊 API Usage Statistics:")
        print(f"   Total calls: {self.total_calls} ({self.failed_calls} failed)")
        print(f"   Elapsed time: {elapsed/60:.1f} minutes")
        print(f"   Average: {self.total_calls/(elapsed/60):.1f} calls/minute")
        
        for i, tracker in enumerate(self.trackers):
            stats = tracker.get_stats()
            print(f"   Key {i+1}: {stats['minute']}/250 min | {stats['hour']}/2000 hr | {stats['day']}/10000 day")
    
    def fetch_match_league_data(self, match_ids: List[str]) -> Dict:
        """
        Fetch league/tier data for a batch of match IDs
        
        Returns dict mapping match_id -> league data
        """
        # Wait for an available key
        key_idx = self.wait_for_available_key()
        
        # GraphQL query to get league information
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
            "authorization": f"bearer {self.get_current_key()}",
            "content-type": "application/json",
            "origin": "https://stratz.com",
            "referer": "https://stratz.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    STRATZ_API_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=30
                )
                
                # Record the call
                self.trackers[key_idx].record_call()
                self.total_calls += 1
                
                if response.status_code == 429:  # Rate limited
                    print(f"  ⚠️  Key {key_idx+1} rate limited (unexpected), rotating...")
                    self.failed_calls += 1
                    # Force use of different key
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    time.sleep(2)
                    return self.fetch_match_league_data(match_ids)
                
                if response.status_code == 401:  # Unauthorized
                    print(f"  ❌ Key {key_idx+1} invalid, trying next key...")
                    self.failed_calls += 1
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    return self.fetch_match_league_data(match_ids)
                
                response.raise_for_status()
                data = response.json()
                
                if "errors" in data:
                    print(f"  GraphQL errors: {data['errors']}")
                    self.failed_calls += 1
                    return {}
                
                # Parse response into dict
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
                print(f"  Request error (attempt {attempt+1}/{max_retries}): {e}")
                self.failed_calls += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return {}
        
        return {}


def load_matches(filepath: str) -> Dict:
    """Load the matches JSON file"""
    print(f"Loading matches from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} matches")
    return data


def save_matches(filepath: str, data: Dict):
    """Save the enhanced matches JSON file"""
    print(f"\nSaving enhanced data to {filepath}...")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print("Save complete!")


def process_matches(matches: Dict, api_client: StratzAPIClient, batch_size: int = 50):
    """
    Process all matches and add league/tier data
    """
    match_ids = list(matches.keys())
    total_matches = len(match_ids)
    total_batches = (total_matches + batch_size - 1) // batch_size
    processed = 0
    added_data = 0
    
    # Estimate time
    print(f"\n📋 Processing Plan:")
    print(f"   Total matches: {total_matches:,}")
    print(f"   Batch size: {batch_size}")
    print(f"   Total API calls: {total_batches:,}")
    print(f"   API keys: {len(api_client.api_keys)}")
    
    # With 5 keys at 250/min each = 1250/min total theoretical max
    # Conservative estimate: 800 calls/minute to stay safe
    estimated_minutes = total_batches / 800
    print(f"   Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")
    
    print(f"\n🚀 Starting processing...\n")
    start_time = time.time()
    
    for i in range(0, total_matches, batch_size):
        batch_ids = match_ids[i:i+batch_size]
        batch_num = i//batch_size + 1
        
        print(f"Batch {batch_num}/{total_batches} (matches {i+1}-{min(i+batch_size, total_matches)})...", end=" ")
        
        league_data = api_client.fetch_match_league_data(batch_ids)
        
        # Add league data to matches
        for match_id in batch_ids:
            if match_id in league_data:
                matches[match_id].update(league_data[match_id])
                if league_data[match_id].get("leagueTier") is not None:
                    added_data += 1
            else:
                # Add null values if no data found
                matches[match_id].update({
                    "leagueId": None,
                    "leagueName": None,
                    "leagueTier": None
                })
        
        processed += len(batch_ids)
        percent = 100 * processed / total_matches
        print(f"✓ ({percent:.1f}% | {added_data} with tier data)")
        
        # Print detailed stats every 100 batches
        if batch_num % 100 == 0:
            api_client.print_stats()
            elapsed = time.time() - start_time
            remaining_batches = total_batches - batch_num
            rate = batch_num / (elapsed / 60)  # batches per minute
            eta = remaining_batches / rate if rate > 0 else 0
            print(f"   ETA: {eta:.1f} minutes\n")
    
    elapsed_total = time.time() - start_time
    print(f"\n✅ Complete! Added tier data to {added_data}/{total_matches} matches")
    print(f"   Total time: {elapsed_total/60:.1f} minutes")
    print(f"   Average rate: {total_batches/(elapsed_total/60):.1f} calls/minute")
    
    return matches


def main():
    """Main execution"""
    import sys
    
    print("=" * 70)
    print("Dota 2 Pro Matches - League/Tier Data Enrichment")
    print("=" * 70)
    
    # Check if API keys are provided
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys to the script!")
        print("Edit the API_KEYS list at the top of this file.\n")
        sys.exit(1)
    
    # Initialize API client
    print(f"\nInitializing with {len(API_KEYS)} API keys...")
    print(f"Rate limits per key: {RATE_LIMITS['second']}/sec, {RATE_LIMITS['minute']}/min, "
          f"{RATE_LIMITS['hour']}/hour, {RATE_LIMITS['day']}/day")
    api_client = StratzAPIClient(API_KEYS)
    
    # Load existing matches
    input_file = "stratz_clean_96507.json"
    matches = load_matches(input_file)
    
    # Process matches and add league data
    enhanced_matches = process_matches(matches, api_client)
    
    # Final statistics
    api_client.print_stats()
    
    # Save enhanced dataset
    output_file = "stratz_with_tiers_96507.json"
    save_matches(output_file, enhanced_matches)
    
    print(f"\n✓ Enhanced dataset saved to {output_file}")
    print("The dataset now includes: leagueId, leagueName, and leagueTier for each match")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
