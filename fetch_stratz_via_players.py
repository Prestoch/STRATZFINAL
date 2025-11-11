#!/usr/bin/env python3
"""
Fetch pro matches from Stratz using PLAYER QUERIES (confirmed working!)

Strategy:
1. Query top pro players' recent matches
2. Collect unique match IDs (filter for leagueId > 0)
3. Get full match details with heroes, roles, tier

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

# Top pro players Steam IDs (from liquipedia/dotabuff)
# Add more for better coverage!
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
    # Add more pro player IDs here for better coverage
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
    
    def get_player_matches(self, steam_id: int, take: int = 100) -> List[Dict]:
        """Get recent matches for a player (THIS WORKS!)"""
        
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
                "skip": 0
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
                    return data["data"]["player"].get("matches", [])
            
            self.failed_calls += 1
            return []
            
        except Exception as e:
            self.failed_calls += 1
            return []
    
    def get_match_details(self, match_id: int) -> Dict:
        """Get full match details (THIS WORKS!)"""
        
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
    
    # Position enum to role mapping
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
    print("Fetch Pro Matches from Stratz via Player Queries")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    print(f"\n📝 Strategy:")
    print(f"   1. Query {len(TOP_PRO_PLAYERS)} pro players for recent matches")
    print(f"   2. Collect unique match IDs (with leagueId > 0)")
    print(f"   3. Get full match details with heroes, roles, tier")
    
    api_client = StratzAPIClient(API_KEYS)
    
    # Step 1: Discover match IDs from pro players
    print(f"\n🔍 Step 1: Discovering match IDs from pro players...")
    
    all_match_ids: Set[int] = set()
    cutoff_time = int((datetime.now() - timedelta(days=180)).timestamp())
    
    for i, steam_id in enumerate(TOP_PRO_PLAYERS):
        print(f"   Player {i+1}/{len(TOP_PRO_PLAYERS)} (ID: {steam_id})...", end=" ")
        
        matches = api_client.get_player_matches(steam_id, take=100)
        
        # Filter for pro matches (leagueId > 0) in time range
        pro_matches = [
            m for m in matches 
            if m.get("leagueId") and m.get("leagueId") > 0 
            and m.get("startDateTime", 0) >= cutoff_time
        ]
        
        if pro_matches:
            for match in pro_matches:
                all_match_ids.add(match["id"])
            print(f"✓ {len(pro_matches)} pro matches (total: {len(all_match_ids)})")
        else:
            print("no recent pro matches")
        
        time.sleep(0.1)
    
    print(f"\n✓ Discovered {len(all_match_ids)} unique pro matches")
    
    if len(all_match_ids) == 0:
        print("\n❌ No matches found! Try adding more pro player IDs.")
        sys.exit(1)
    
    # Step 2: Get full match details
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
    output_file = f"stratz_pro_matches_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"✓ Saved!")
    
    # Stats
    elapsed = time.time() - api_client.start_time
    print(f"\n📊 Statistics:")
    print(f"   Pro players queried: {len(TOP_PRO_PLAYERS)}")
    print(f"   Unique matches found: {len(all_match_ids)}")
    print(f"   Successfully fetched: {successful}")
    print(f"   Total API calls: {api_client.total_calls}")
    print(f"   Failed calls: {api_client.failed_calls}")
    print(f"   Time: {elapsed/60:.1f} minutes")
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Output: {output_file}")
    print("\n📋 Data included:")
    print("   ✓ Match IDs")
    print("   ✓ Heroes (radiant/dire)")
    print("   ✓ Roles (carry, mid, offlane, support)")
    print("   ✓ League names")
    print("   ✓ League tiers (PREMIUM, PROFESSIONAL, etc.)")
    print("\n💡 To get more matches, add more pro player Steam IDs to the script!")


if __name__ == "__main__":
    main()
