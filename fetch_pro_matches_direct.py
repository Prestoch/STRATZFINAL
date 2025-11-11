#!/usr/bin/env python3
"""
Fetch recent pro matches by querying matches directly (not through leagues)
Works without admin access!

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
    
    def search_pro_matches(self, start_time: int, end_time: int, skip: int = 0, take: int = 50) -> List[Dict]:
        """Search for pro matches directly using filters"""
        
        key_idx = self.wait_for_available_key()
        
        # Query matches with pro filters
        # Stratz considers matches with leagueId > 0 as pro matches
        query = """
        query SearchMatches($request: MatchRequestType!) {
            matches(request: $request) {
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
                    steamAccountId
                    heroId
                    isRadiant
                    position
                    role
                }
            }
        }
        """
        
        variables = {
            "request": {
                "startDateTime": start_time,
                "endDateTime": end_time,
                "isPro": True,  # Filter for pro matches only
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
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    time.sleep(2)
                    continue
                
                if response.status_code != 200:
                    self.failed_calls += 1
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    print(f"  ❌ HTTP {response.status_code}: {response.text[:100]}")
                    return []
                
                data = response.json()
                
                if "errors" in data:
                    self.failed_calls += 1
                    print(f"  ❌ GraphQL error: {data['errors']}")
                    return []
                
                if "data" in data and "matches" in data["data"]:
                    return data["data"]["matches"] or []
                
                return []
                
            except Exception as e:
                self.failed_calls += 1
                print(f"  ❌ Error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return []
        
        return []


def parse_match_data(match: Dict) -> Dict:
    """Parse match data into the desired format"""
    
    radiant_players = [p for p in match.get("players", []) if p.get("isRadiant")]
    dire_players = [p for p in match.get("players", []) if not p.get("isRadiant")]
    
    # Map position to role
    position_to_role = {
        0: "carry",
        1: "mid", 
        2: "offlane",
        3: "softsupport",
        4: "hardsupport"
    }
    
    radiant_roles = []
    for player in radiant_players:
        role = position_to_role.get(player.get("position"), player.get("role", "unknown"))
        radiant_roles.append({
            "heroId": player.get("heroId"),
            "role": role
        })
    
    dire_roles = []
    for player in dire_players:
        role = position_to_role.get(player.get("position"), player.get("role", "unknown"))
        dire_roles.append({
            "heroId": player.get("heroId"),
            "role": role
        })
    
    result = {
        "radiantWin": match.get("didRadiantWin", False),
        "radiantRoles": radiant_roles,
        "direRoles": dire_roles,
        "leagueId": match.get("leagueId"),
        "leagueName": match.get("league", {}).get("displayName") if match.get("league") else None,
        "leagueTier": match.get("league", {}).get("tier") if match.get("league") else None
    }
    
    return result


def main():
    import sys
    
    print("=" * 70)
    print("Fetch Recent Pro Matches from Stratz (Direct Query)")
    print("=" * 70)
    
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("\n❌ ERROR: Please add your Stratz API keys!")
        sys.exit(1)
    
    print(f"\n📅 Time Range:")
    print(f"   Start: {datetime.fromtimestamp(START_TIME).strftime('%Y-%m-%d')}")
    print(f"   End: {datetime.fromtimestamp(END_TIME).strftime('%Y-%m-%d')}")
    print(f"   Duration: 6 months")
    print(f"\n🎯 Method: Direct match query (no admin required)")
    print(f"   Using {len(API_KEYS)} API keys")
    
    api_client = StratzAPIClient(API_KEYS)
    
    all_matches = {}
    
    print(f"\n🔍 Searching for pro matches...")
    
    skip = 0
    take = 50  # Fetch 50 matches at a time
    total_fetched = 0
    
    while True:
        print(f"   Fetching matches {skip+1}-{skip+take}...")
        
        matches = api_client.search_pro_matches(START_TIME, END_TIME, skip, take)
        
        if not matches:
            print(f"   No more matches found.")
            break
        
        # Parse and store matches
        for match in matches:
            if match and match.get("id"):
                match_id = str(match["id"])
                parsed_data = parse_match_data(match)
                all_matches[match_id] = parsed_data
                total_fetched += 1
        
        print(f"     ✓ Found {len(matches)} matches (total: {total_fetched})")
        
        # If we got fewer matches than requested, we've reached the end
        if len(matches) < take:
            break
        
        skip += take
        time.sleep(0.5)  # Small delay between requests
        
        # Safety limit to prevent infinite loop
        if skip > 50000:
            print(f"   Reached safety limit (50,000 matches)")
            break
    
    print(f"\n✅ Total matches found: {len(all_matches)}")
    
    if len(all_matches) == 0:
        print("\n⚠️  No pro matches found!")
        print("Possible reasons:")
        print("  - isPro filter might not work without admin")
        print("  - Time range has no pro matches")
        print("  - API endpoint changed")
        print("\nTrying alternative approach...")
        
        # Alternative: Just fetch recent matches with leagueId filter
        print("\n🔄 Alternative: Fetching matches with leagueId > 0...")
        
        # This would require a different query structure
        print("   (This requires manual match ID list)")
        print("   Recommendation: Use your existing match IDs and enrich them")
    
    # Save results
    output_file = f"stratz_pro_matches_6months_{datetime.now().strftime('%Y%m%d')}.json"
    
    if len(all_matches) > 0:
        print(f"\n💾 Saving to {output_file}...")
        with open(output_file, 'w') as f:
            json.dump(all_matches, f, indent=2)
        print(f"✓ Saved {len(all_matches)} matches")
    
    # Stats
    elapsed = time.time() - api_client.start_time
    print(f"\n📊 Statistics:")
    print(f"   Total API calls: {api_client.total_calls}")
    print(f"   Failed calls: {api_client.failed_calls}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    if elapsed > 0:
        print(f"   Average rate: {api_client.total_calls/(elapsed/60):.1f} calls/min")
    
    print("\n" + "=" * 70)
    
    if len(all_matches) > 0:
        print(f"✓ Done! Output: {output_file}")
    else:
        print("❌ No matches fetched")
        print("\n💡 RECOMMENDATION:")
        print("   Stratz API requires admin access for most pro match discovery.")
        print("   Better approach: Use existing match IDs from other sources:")
        print("   - OpenDota API (free, no auth)")
        print("   - Dotabuff")
        print("   - Or your existing stratz_clean_96507.json dataset")


if __name__ == "__main__":
    main()
