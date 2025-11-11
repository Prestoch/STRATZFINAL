#!/usr/bin/env python3
"""
Script to fetch league/tier data with CHECKPOINT/RESUME support.
If network fails or you stop the script, it can resume from where it left off.

Install: pip install cloudscraper
"""

import json
import time
import cloudscraper
import os
from typing import Dict, List, Optional
from collections import deque

STRATZ_API_URL = "https://api.stratz.com/graphql"

API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

RATE_LIMITS = {
    'second': 15,
    'minute': 200,
    'hour': 1600,
    'day': 8000
}

# Checkpoint settings
CHECKPOINT_INTERVAL = 1000  # Save progress every 1000 matches
CHECKPOINT_FILE = "stratz_checkpoint.json"


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
        self.network_errors = 0
        self.start_time = time.time()
        
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
        print(f"   Total calls: {self.total_calls} ({self.failed_calls} failed, {self.network_errors} network errors)")
        print(f"   Elapsed time: {elapsed/60:.1f} minutes")
        if elapsed > 0:
            print(f"   Average: {self.total_calls/(elapsed/60):.1f} calls/minute")
        
        for i, tracker in enumerate(self.trackers):
            stats = tracker.get_stats()
            print(f"   Key {i+1}: {stats['minute']}/200 min | {stats['hour']}/1600 hr | {stats['day']}/8000 day")
    
    def fetch_single_match_league_data(self, match_id: str) -> Dict:
        """Fetch league/tier data for a SINGLE match with network error handling"""
        
        key_idx = self.wait_for_available_key()
        
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
        
        max_retries = 5  # Increased for network resilience
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
                    continue
                
                if response.status_code == 401:
                    self.failed_calls += 1
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    return {}
                
                if response.status_code != 200:
                    self.failed_calls += 1
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {}
                
                data = response.json()
                
                if "errors" in data:
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
                
            except (ConnectionError, TimeoutError, Exception) as e:
                self.network_errors += 1
                print(f"  ⚠️  Network error (attempt {attempt+1}/{max_retries}): {str(e)[:50]}")
                
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 30)  # Max 30 second wait
                    print(f"  Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  ❌ Giving up on match {match_id} after {max_retries} attempts")
                    return {}
        
        return {}


def load_checkpoint() -> Optional[Dict]:
    """Load checkpoint if it exists"""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint = json.load(f)
            print(f"✓ Found checkpoint: {checkpoint['processed']}/{checkpoint['total']} matches processed")
            return checkpoint
        except:
            return None
    return None


def save_checkpoint(matches: Dict, processed_ids: List[str], stats: Dict):
    """Save current progress"""
    checkpoint = {
        'processed': len(processed_ids),
        'total': len(matches),
        'processed_ids': processed_ids,
        'timestamp': time.time(),
        'stats': stats,
        'matches': matches
    }
    
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    print(f"  💾 Checkpoint saved ({len(processed_ids)} matches)")


def load_matches(filepath: str) -> Dict:
    print(f"Loading matches from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} matches")
    return data


def save_final_matches(filepath: str, data: Dict):
    print(f"\n💾 Saving final enhanced data to {filepath}...")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print("✓ Save complete!")
    
    # Clean up checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("✓ Checkpoint file cleaned up")


def process_matches(matches: Dict, api_client: StratzAPIClient):
    """Process all matches with checkpoint/resume support"""
    
    # Check for existing checkpoint
    checkpoint = load_checkpoint()
    
    if checkpoint:
        print("\n🔄 RESUMING from checkpoint...")
        matches = checkpoint['matches']
        processed_ids = set(checkpoint['processed_ids'])
        match_ids = [mid for mid in matches.keys() if mid not in processed_ids]
        already_processed = len(processed_ids)
    else:
        print("\n🆕 Starting fresh (no checkpoint found)...")
        match_ids = list(matches.keys())
        processed_ids = set()
        already_processed = 0
    
    total_matches = len(matches)
    processed = already_processed
    added_data = already_processed  # Estimate
    
    print(f"\n📋 Processing Plan:")
    print(f"   Total matches: {total_matches:,}")
    print(f"   Already processed: {already_processed:,}")
    print(f"   Remaining: {len(match_ids):,}")
    print(f"   Checkpoint interval: Every {CHECKPOINT_INTERVAL} matches")
    
    if len(match_ids) > 0:
        estimated_minutes = len(match_ids) / 800
        print(f"   Estimated time: {estimated_minutes:.1f} minutes ({estimated_minutes/60:.1f} hours)")
    
    print(f"\n🚀 Starting processing...\n")
    start_time = time.time()
    
    try:
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
            
            processed_ids.add(match_id)
            processed += 1
            
            # Progress update every 100 matches
            if processed % 100 == 0:
                percent = 100 * processed / total_matches
                print(f"Progress: {processed}/{total_matches} ({percent:.1f}%) | {added_data} with tier data")
            
            # Save checkpoint every CHECKPOINT_INTERVAL matches
            if processed % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(matches, list(processed_ids), {
                    'total_calls': api_client.total_calls,
                    'failed_calls': api_client.failed_calls,
                    'network_errors': api_client.network_errors
                })
                api_client.print_stats()
                
                elapsed = time.time() - start_time
                remaining = total_matches - processed
                rate = (processed - already_processed) / (elapsed / 60) if elapsed > 0 else 0
                eta = remaining / rate if rate > 0 else 0
                print(f"   ETA: {eta:.1f} minutes\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user!")
        print("Saving checkpoint...")
        save_checkpoint(matches, list(processed_ids), {
            'total_calls': api_client.total_calls,
            'failed_calls': api_client.failed_calls,
            'network_errors': api_client.network_errors
        })
        print("✓ Progress saved. Run the script again to resume from here.")
        return None
    
    elapsed_total = time.time() - start_time
    print(f"\n✅ Complete! Added tier data to {added_data}/{total_matches} matches")
    print(f"   Total time: {elapsed_total/60:.1f} minutes ({elapsed_total/3600:.2f} hours)")
    if elapsed_total > 0:
        print(f"   Average rate: {(processed - already_processed)/(elapsed_total/60):.1f} calls/minute")
    
    return matches


def main():
    import sys
    
    print("=" * 70)
    print("Dota 2 League/Tier Enrichment (with CHECKPOINT/RESUME)")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    print(f"\nFeatures:")
    print(f"  ✓ Cloudflare bypass with cloudscraper")
    print(f"  ✓ Checkpoint every {CHECKPOINT_INTERVAL} matches")
    print(f"  ✓ Resume from checkpoint if interrupted")
    print(f"  ✓ Network error resilience (5 retries)")
    print(f"  ✓ Using {len(API_KEYS)} API keys")
    
    api_client = StratzAPIClient(API_KEYS)
    
    input_file = "stratz_clean_96507.json"
    
    # Load matches (or from checkpoint)
    checkpoint = load_checkpoint()
    if checkpoint and 'matches' in checkpoint:
        print("\nLoading matches from checkpoint...")
        matches = checkpoint['matches']
    else:
        matches = load_matches(input_file)
    
    enhanced_matches = process_matches(matches, api_client)
    
    if enhanced_matches is None:
        print("\n⚠️  Script was interrupted. Progress has been saved.")
        print("Run the script again to resume.")
        sys.exit(0)
    
    api_client.print_stats()
    
    output_file = "stratz_with_tiers_96507.json"
    save_final_matches(output_file, enhanced_matches)
    
    print(f"\n✓ Enhanced dataset saved to {output_file}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
