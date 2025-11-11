#!/usr/bin/env python3
"""
Fetch pro matches from Stratz using WORKING queries (no admin needed!)

Based on successful query discovery:
- leagues() query works
- league.matches(request: {...}) works with proper request type
- player.matches() works

Install: pip install cloudscraper
"""

import json
import time
import cloudscraper
from datetime import datetime, timedelta
from typing import Dict, List, Optional

STRATZ_API_URL = "https://api.stratz.com/graphql"

API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

RATE_LIMITS = {'second': 15, 'minute': 200, 'hour': 1600, 'day': 8000}

# Time range: last 6 months
END_TIME = int(datetime.now().timestamp())
START_TIME = int((datetime.now() - timedelta(days=180)).timestamp())

# Pro tiers
PRO_TIERS = ["PROFESSIONAL", "PREMIUM", "DPC_QUALIFIER", "DPC_LEAGUE_QUALIFIER", 
             "DPC_LEAGUE", "DPC_LEAGUE_FINALS", "MAJOR", "MINOR", "INTERNATIONAL"]


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
    
    def get_leagues_in_timerange(self, start_time: int, end_time: int, tiers: List[str]) -> List[Dict]:
        """Get leagues in time range (this works!)"""
        
        key_idx = self.wait_for_available_key()
        
        query = """
        query GetLeagues($request: LeagueRequestType!) {
            leagues(request: $request) {
                id
                displayName
                tier
            }
        }
        """
        
        variables = {
            "request": {
                "tiers": tiers,
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
                if "data" in data and "leagues" in data["data"]:
                    return data["data"]["leagues"] or []
            
            self.failed_calls += 1
            return []
            
        except Exception as e:
            self.failed_calls += 1
            return []
    
    def get_league_matches(self, league_id: int, skip: int = 0, take: int = 100) -> List[int]:
        """Get match IDs from a specific league using correct request type"""
        
        key_idx = self.wait_for_available_key()
        
        # Use the correct request parameter type
        query = """
        query GetLeagueMatches($leagueId: Int!, $request: LeagueMatchesRequestType!) {
            league(id: $leagueId) {
                id
                matches(request: $request) {
                    id
                }
            }
        }
        """
        
        variables = {
            "leagueId": league_id,
            "request": {
                "skip": skip,
                "take": take
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
                
                if "errors" in data:
                    # If it still fails, skip this league
                    return []
                
                if "data" in data and "league" in data["data"] and data["data"]["league"]:
                    matches = data["data"]["league"].get("matches", [])
                    return [m["id"] for m in matches if m]
            
            self.failed_calls += 1
            return []
            
        except Exception as e:
            self.failed_calls += 1
            return []
    
    def get_match_details(self, match_id: int) -> Optional[Dict]:
        """Get full match details (we know this works!)"""
        
        key_idx = self.wait_for_available_key()
        
        query = """
        query GetMatch($id: Long!) {
            match(id: $id) {
                id
                didRadiantWin
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
    
    position_to_role = {
        0: "carry",
        1: "mid",
        2: "offlane",
        3: "softsupport",
        4: "hardsupport"
    }
    
    radiant_roles = []
    dire_roles = []
    
    for player in match.get("players", []):
        pos = player.get("position")
        role = position_to_role.get(pos, player.get("role", "unknown"))
        
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
    print("Fetch Pro Matches from Stratz (Using Working Queries!)")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    print(f"\n📅 Time Range:")
    print(f"   Start: {datetime.fromtimestamp(START_TIME).strftime('%Y-%m-%d')}")
    print(f"   End: {datetime.fromtimestamp(END_TIME).strftime('%Y-%m-%d')}")
    
    api_client = StratzAPIClient(API_KEYS)
    
    # Step 1: Get leagues
    print(f"\n🔍 Step 1: Finding leagues in time range...")
    
    leagues = api_client.get_leagues_in_timerange(START_TIME, END_TIME, PRO_TIERS)
    print(f"   ✓ Found {len(leagues)} leagues")
    
    if len(leagues) == 0:
        print("\n⚠️  No leagues found in this time range.")
        print("Trying extended time range...")
        # Try wider range
        extended_start = int((datetime.now() - timedelta(days=365)).timestamp())
        leagues = api_client.get_leagues_in_timerange(extended_start, END_TIME, PRO_TIERS)
        print(f"   ✓ Found {len(leagues)} leagues in extended range")
    
    # Step 2: Get match IDs from each league
    print(f"\n📋 Step 2: Getting matches from leagues...")
    
    all_match_ids = set()
    
    for league in leagues:
        league_id = league["id"]
        league_name = league["displayName"]
        
        print(f"   Fetching {league_name} (ID: {league_id})...")
        
        skip = 0
        take = 100
        while True:
            match_ids = api_client.get_league_matches(league_id, skip, take)
            
            if not match_ids:
                break
            
            all_match_ids.update(match_ids)
            print(f"     • Got {len(match_ids)} matches (total: {len(all_match_ids)})")
            
            if len(match_ids) < take:
                break
            
            skip += take
            time.sleep(0.3)
    
    print(f"\n✓ Discovered {len(all_match_ids)} unique matches")
    
    if len(all_match_ids) == 0:
        print("\n❌ No matches found!")
        print("This might mean:")
        print("  - league.matches(request:) still requires admin")
        print("  - Need to use alternative approach (OpenDota hybrid)")
        sys.exit(1)
    
    # Step 3: Get match details
    print(f"\n📥 Step 3: Fetching match details...")
    
    all_matches = {}
    match_ids_list = list(all_match_ids)
    processed = 0
    
    for match_id in match_ids_list:
        match_data = api_client.get_match_details(match_id)
        
        if match_data:
            parsed = parse_match_data(match_data)
            all_matches[str(match_id)] = parsed
        
        processed += 1
        
        if processed % 100 == 0:
            percent = 100 * processed / len(match_ids_list)
            print(f"   Progress: {processed}/{len(match_ids_list)} ({percent:.1f}%)")
    
    print(f"\n✅ Fetched {len(all_matches)} matches")
    
    # Save
    output_file = f"stratz_pro_matches_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"✓ Saved!")
    
    # Stats
    elapsed = time.time() - api_client.start_time
    print(f"\n📊 Statistics:")
    print(f"   Total API calls: {api_client.total_calls}")
    print(f"   Failed calls: {api_client.failed_calls}")
    print(f"   Time: {elapsed/60:.1f} minutes")
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Output: {output_file}")


if __name__ == "__main__":
    main()
