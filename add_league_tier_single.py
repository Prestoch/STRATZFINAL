#!/usr/bin/env python3
"""
Script to fetch league/tier data for Dota 2 pro matches from Stratz API
Queries matches ONE AT A TIME (batch queries require admin access)

Install: pip install cloudscraper
"""

import json
import time
import cloudscraper
from typing import Dict, List, Optional
from collections import deque

# Stratz GraphQL endpoint
STRATZ_API_URL = "https://api.stratz.com/graphql"

# API keys
API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

# Rate limits (80% of actual: 15/sec, 200/min, 1600/hour, 8000/day per key)
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
        now = time.time()
        self.calls_second.append(now)
        self.calls_minute.append(now)
        self.calls_hour.append(now)
        self.calls_day.append(now)
        
    def clean_old_calls(self):
        now = time.time()
        self.calls_second = [t for t in self.calls_second if now - t < 1]
        self.calls_minute = [t for t in self.calls_minute if now - t < 60]
        self.calls_hour = [t for t in self.calls_hour if now - t < 3600]
        self.calls_day = [t for t in self.calls_day if now - t < 86400]
        
    def can_make_call(self) -> bool:
        self.clean_old_calls()
        return (
            len(self.calls_second) < RATE_LIMITS['second'] and
            len(self.calls_minute) < RATE_LIMITS['minute'] and
            len(self.calls_hour) < RATE_LIMITS['hour'] and
            len(self.calls_day) < RATE_LIMITS['day']
        )
    
    def time_until_available(self) -> float:
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
        
        # Create cloudscraper session (bypasses Cloudflare)
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )
        
    def get_available_key_index(self) -> Optional[int]:
        if self.trackers[self.current_key_index].can_make_call():
            return self.current_key_index
        
        for i in range(len(self.api_keys)):
            if self.trackers[i].can_make_call():
                return i
                
        return None
    
    def wait_for_available_key(self) -> int:
        while True:
            key_idx = self.get_available_key_index()
            if key_idx is not None:
                self.current_key_index = key_idx
                return key_idx
            
            wait_times = [tracker.time_until_available() for tracker in self.trackers]
            min_wait = min(wait_times)
            
            if min_wait > 0:
                print(f"  ⏳ Rate limit reached. Waiting {min_wait:.1f}s...")
                time.sleep(min_wait + 0.1)
            else:
                time.sleep(0.1)
    
    def get_current_key(self) -> str:
        return self.api_keys[self.current_key_index]
    
    def print_stats(self):
        elapsed = time.time() - self.start_time
        print(f"\n📊 API Usage Statistics:")
        print(f"   Total calls: {self.total_calls} ({self.failed_calls} failed)")
        print(f"   Elapsed time: {elapsed/60:.1f} minutes")
        if elapsed > 0:
            print(f"   Average: {self.total_calls/(elapsed/60):.1f} calls/minute")
        
        for i, tracker in enumerate(self.trackers):
            stats = tracker.get_stats()
            print(f"   Key {i+1}: {stats['minute']}/200 min | {stats['hour']}/1600 hr | {stats['day']}/8000 day")
    
    def fetch_single_match_league_data(self, match_id: str) -> Dict:
        """Fetch league/tier data for a SINGLE match"""
        
        key_idx = self.wait_for_available_key()
        
        # Query ONE match (batch queries require admin)
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
        
        variables = {"id": int(match_id)}
        
        headers = {
            "authorization": f"bearer {self.get_current_key()}",
            "content-type": "application/json",
            "origin": "https://stratz.com",
            "referer": "https://stratz.com/",
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.scraper.post(
                    STRATZ_API_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=30
                )
                
                self.trackers[key_idx].record_call()
                self.total_calls += 1
                
                if response.status_code == 429:
                    self.failed_calls += 1
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    time.sleep(2)
                    return self.fetch_single_match_league_data(match_id)
                
                if response.status_code == 401:
                    self.failed_calls += 1
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    return self.fetch_single_match_league_data(match_id)
                
                if response.status_code != 200:
                    self.failed_calls += 1
                    return {}
                
                data = response.json()
                
                if "errors" in data:
                    # Check for specific errors
                    error_msg = str(data["errors"])
                    if "admin" in error_msg.lower():
                        print(f"\n  ❌ Admin error on match {match_id}. Skipping...")
                    self.failed_calls += 1
                    return {}
                
                if "data" in data and "match" in data["data"] and data["data"]["match"]:
                    match = data["data"]["match"]
                    return {
                        "leagueId": match.get("leagueId"),
                        "leagueName": match.get("league", {}).get("displayName") if match.get("league") else None,
                        "leagueTier": match.get("league", {}).get("tier") if match.get("league") else None
                    }
                
                return {}
                
            except Exception as e:
                self.failed_calls += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return {}
        
        return {}


def load_matches(filepath: str) -> Dict:
    print(f"Loading matches from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} matches")
    return data


def save_matches(filepath: str, data: Dict):
    print(f"\nSaving enhanced data to {filepath}...")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print("Save complete!")


def process_matches(matches: Dict, api_client: StratzAPIClient):
    """Process all matches ONE AT A TIME"""
    
    match_ids = list(matches.keys())
    total_matches = len(match_ids)
    processed = 0
    added_data = 0
    
    print(f"\n📋 Processing Plan:")
    print(f"   Total matches: {total_matches:,}")
    print(f"   Mode: ONE match per API call (batch queries need admin)")
    print(f"   API keys: {len(api_client.api_keys)}")
    
    # With 5 keys at 200/min each = 1000 calls/min theoretical
    # Conservative: ~800/min
    estimated_minutes = total_matches / 800
    print(f"   Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")
    
    print(f"\n🚀 Starting processing...\n")
    start_time = time.time()
    
    for i, match_id in enumerate(match_ids):
        league_data = api_client.fetch_single_match_league_data(match_id)
        
        if league_data:
            matches[match_id].update(league_data)
            if league_data.get("leagueTier") is not None:
                added_data += 1
        else:
            matches[match_id].update({
                "leagueId": None,
                "leagueName": None,
                "leagueTier": None
            })
        
        processed += 1
        
        # Progress update every 100 matches
        if processed % 100 == 0:
            percent = 100 * processed / total_matches
            print(f"Progress: {processed}/{total_matches} ({percent:.1f}%) | {added_data} with tier data")
        
        # Detailed stats every 1000 matches
        if processed % 1000 == 0:
            api_client.print_stats()
            elapsed = time.time() - start_time
            remaining = total_matches - processed
            rate = processed / (elapsed / 60)
            eta = remaining / rate if rate > 0 else 0
            print(f"   ETA: {eta:.1f} minutes\n")
    
    elapsed_total = time.time() - start_time
    print(f"\n✅ Complete! Added tier data to {added_data}/{total_matches} matches")
    print(f"   Total time: {elapsed_total/60:.1f} minutes ({elapsed_total/3600:.2f} hours)")
    print(f"   Average rate: {total_matches/(elapsed_total/60):.1f} calls/minute")
    
    return matches


def main():
    import sys
    
    print("=" * 70)
    print("Dota 2 League/Tier Enrichment (Single-Match Queries)")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    print(f"\nUsing {len(API_KEYS)} API keys with cloudscraper (Cloudflare bypass)")
    
    api_client = StratzAPIClient(API_KEYS)
    
    input_file = "stratz_clean_96507.json"
    matches = load_matches(input_file)
    
    enhanced_matches = process_matches(matches, api_client)
    
    api_client.print_stats()
    
    output_file = "stratz_with_tiers_96507.json"
    save_matches(output_file, enhanced_matches)
    
    print(f"\n✓ Enhanced dataset saved to {output_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
