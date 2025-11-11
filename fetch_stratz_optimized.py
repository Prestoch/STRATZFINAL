#!/usr/bin/env python3
"""
OPTIMIZED Stratz Pro Match Fetcher
Uses time filters + pagination for maximum efficiency

Based on test results:
- Max 100 matches per query
- Pagination works (skip parameter)
- Time filters work (startDateTime/endDateTime)
- Can get ALL matches for last 6 months

Install: pip install cloudscraper
"""

import json
import time
import cloudscraper
from datetime import datetime, timedelta
from typing import Dict, List, Set

STRATZ_API_URL = "https://api.stratz.com/graphql"

API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

RATE_LIMITS = {'second': 15, 'minute': 200, 'hour': 1600, 'day': 8000}

# Time range (6 months)
MONTHS_BACK = 6

# Top pro players (add more for better coverage!)
TOP_PRO_PLAYERS = [
    111620041,   # Dendi
    86745912,    # Arteezy
    86727555,    # SumaiL
    88719902,    # Miracle-
    101495620,   # Ame
    106863163,   # Paparazzi
    108382060,   # Somnus
    108452107,   # NothingToSay
    129958758,   # Yatoro
    134556694,   # MATUMBAMAN
    138857296,   # Crystallis
    139876032,   # GH
    146775073,   # Ceb
    162185555,   # w33
    178949121,   # MidOne
    19672354,    # Puppey
    25907144,    # KuroKy
    26771994,    # SuperNova
    311360822,   # bzm
    359584783,   # Collapse
    389728883,   # TorontoTokyo
    416961708,   # Mira
    441562690,   # Pure
    86698277,    # N0tail
    86717663,    # JerAx
    89871557,    # Topson
    94049589,    # ana
    94338967,    # Zai
    98878010,    # Quinn
]


class RateLimitTracker:
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


class StratzAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = api_keys
        self.trackers = [RateLimitTracker(i) for i in range(len(api_keys))]
        self.current_key_index = 0
        self.total_calls = 0
        self.failed_calls = 0
        self.start_time = time.time()
        
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )
        
    def wait_for_available_key(self) -> int:
        while True:
            if self.trackers[self.current_key_index].can_make_call():
                return self.current_key_index
            
            for i in range(len(self.api_keys)):
                if self.trackers[i].can_make_call():
                    self.current_key_index = i
                    return i
            
            wait_times = [t.time_until_available() for t in self.trackers]
            min_wait = min(wait_times)
            if min_wait > 0:
                print(f"  ⏳ Rate limit. Waiting {min_wait:.1f}s...")
                time.sleep(min_wait + 0.1)
    
    def get_player_matches_paginated(self, steam_id: int, start_time: int, end_time: int) -> List[Dict]:
        """Get ALL player matches in time range using pagination"""
        
        all_matches = []
        skip = 0
        take = 100  # Max allowed
        
        while True:
            key_idx = self.wait_for_available_key()
            
            query = """
            query GetPlayerMatches($steamAccountId: Long!, $request: PlayerMatchesRequestType!) {
                player(steamAccountId: $steamAccountId) {
                    matches(request: $request) {
                        id
                        leagueId
                        startDateTime
                    }
                }
            }
            """
            
            variables = {
                "steamAccountId": steam_id,
                "request": {
                    "take": take,
                    "skip": skip,
                    "startDateTime": start_time,
                    "endDateTime": end_time
                }
            }
            
            headers = {
                "authorization": f"bearer {self.api_keys[key_idx]}",
                "content-type": "application/json",
                "origin": "https://stratz.com",
                "referer": "https://stratz.com/",
            }
            
            try:
                response = self.scraper.post(
                    STRATZ_API_URL,
                    json={"query": query, "variables": variables},
                    headers=headers,
                    timeout=30
                )
                
                self.trackers[key_idx].record_call()
                self.total_calls += 1
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "player" in data["data"]:
                        matches = data["data"]["player"].get("matches", [])
                        
                        if not matches:
                            break  # No more matches
                        
                        all_matches.extend(matches)
                        
                        if len(matches) < take:
                            break  # Last page
                        
                        skip += take
                        time.sleep(0.1)  # Small delay
                        continue
                
                self.failed_calls += 1
                break
                
            except Exception as e:
                self.failed_calls += 1
                break
        
        return all_matches
    
    def get_match_details(self, match_id: int) -> Dict:
        """Get full match details"""
        
        key_idx = self.wait_for_available_key()
        
        query = """
        query GetMatch($id: Long!) {
            match(id: $id) {
                id
                didRadiantWin
                startDateTime
                leagueId
                league {
                    id
                    displayName
                    tier
                }
                players {
                    heroId
                    isRadiant
                    position
                    role
                }
            }
        }
        """
        
        headers = {
            "authorization": f"bearer {self.api_keys[key_idx]}",
            "content-type": "application/json",
            "origin": "https://stratz.com",
            "referer": "https://stratz.com/",
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.scraper.post(
                    STRATZ_API_URL,
                    json={"query": query, "variables": {"id": match_id}},
                    headers=headers,
                    timeout=30
                )
                
                self.trackers[key_idx].record_call()
                self.total_calls += 1
                
                if response.status_code == 429:
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    time.sleep(2)
                    continue
                
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and "match" in data["data"] and data["data"]["match"]:
                        return data["data"]["match"]
                
                self.failed_calls += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
                    
            except Exception as e:
                self.failed_calls += 1
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        
        return None


def parse_match_data(match: Dict) -> Dict:
    """Parse match into our format"""
    
    position_map = {
        "POSITION_1": "carry",
        "POSITION_2": "mid",
        "POSITION_3": "offlane",
        "POSITION_4": "softsupport",
        "POSITION_5": "hardsupport"
    }
    
    radiant_roles = []
    dire_roles = []
    
    for player in match.get("players", []):
        pos = player.get("position")
        role = position_map.get(pos, "unknown")
        
        entry = {"heroId": player.get("heroId"), "role": role}
        
        if player.get("isRadiant"):
            radiant_roles.append(entry)
        else:
            dire_roles.append(entry)
    
    return {
        "radiantWin": match.get("didRadiantWin", False),
        "radiantRoles": radiant_roles,
        "direRoles": dire_roles,
        "leagueId": match.get("leagueId"),
        "leagueName": match.get("league", {}).get("displayName") if match.get("league") else None,
        "leagueTier": match.get("league", {}).get("tier") if match.get("league") else None
    }


def main():
    import sys
    
    print("=" * 70)
    print("Fetch Pro Matches from Stratz - OPTIMIZED")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    # Time range
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=MONTHS_BACK * 30)).timestamp())
    
    print(f"\n📅 Time Range:")
    print(f"   From: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d')}")
    print(f"   To: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d')}")
    print(f"   Duration: {MONTHS_BACK} months")
    
    print(f"\n📝 Strategy:")
    print(f"   1. Query {len(TOP_PRO_PLAYERS)} pro players")
    print(f"   2. Use time filter + pagination (100 matches per page)")
    print(f"   3. Collect unique match IDs (leagueId > 0)")
    print(f"   4. Get full match details")
    
    api_client = StratzAPIClient(API_KEYS)
    
    # Step 1: Discover match IDs
    print(f"\n🔍 Step 1: Discovering match IDs...")
    
    all_match_ids: Set[int] = set()
    
    for i, steam_id in enumerate(TOP_PRO_PLAYERS):
        print(f"   Player {i+1}/{len(TOP_PRO_PLAYERS)} (ID: {steam_id})...", end=" ")
        
        matches = api_client.get_player_matches_paginated(steam_id, start_time, end_time)
        
        # Filter for pro matches
        pro_matches = [m for m in matches if m.get("leagueId") and m.get("leagueId") > 0]
        
        if pro_matches:
            for match in pro_matches:
                all_match_ids.add(match["id"])
            print(f"✓ {len(pro_matches)} pro matches (total: {len(all_match_ids)})")
        else:
            print("no pro matches")
        
        time.sleep(0.1)
    
    print(f"\n✓ Discovered {len(all_match_ids)} unique pro matches")
    
    if len(all_match_ids) == 0:
        print("\n⚠️  No matches found! Try:")
        print("   - Increasing MONTHS_BACK")
        print("   - Adding more pro player IDs")
        sys.exit(0)
    
    # Step 2: Get full details
    print(f"\n📥 Step 2: Fetching full match details...")
    
    all_matches = {}
    match_ids_list = list(all_match_ids)
    processed = 0
    successful = 0
    
    for match_id in match_ids_list:
        match_data = api_client.get_match_details(match_id)
        
        if match_data:
            parsed = parse_match_data(match_data)
            all_matches[str(match_id)] = parsed
            successful += 1
        
        processed += 1
        
        if processed % 100 == 0:
            percent = 100 * processed / len(match_ids_list)
            print(f"   Progress: {processed}/{len(match_ids_list)} ({percent:.1f}%) | {successful} successful")
    
    print(f"\n✅ Fetched {successful}/{len(match_ids_list)} matches")
    
    # Save
    output_file = f"stratz_pro_{MONTHS_BACK}months_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"✓ Saved!")
    
    # Stats
    elapsed = time.time() - api_client.start_time
    print(f"\n📊 Statistics:")
    print(f"   Players queried: {len(TOP_PRO_PLAYERS)}")
    print(f"   Unique matches: {len(all_match_ids)}")
    print(f"   Successfully fetched: {successful}")
    print(f"   Total API calls: {api_client.total_calls}")
    print(f"   Time: {elapsed/60:.1f} minutes")
    print(f"   Avg rate: {api_client.total_calls/(elapsed/60):.1f} calls/min")
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Output: {output_file}")


if __name__ == "__main__":
    main()
