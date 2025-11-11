#!/usr/bin/env python3
"""
Fetch recent pro matches from OpenDota API (FREE, no API key needed!)
Then enrich with Stratz data

OpenDota is better for discovering matches, Stratz is better for roles/analysis
"""

import json
import time
import requests
import cloudscraper
from datetime import datetime, timedelta
from typing import Dict, List, Optional

OPENDOTA_API = "https://api.opendota.com/api"
STRATZ_API_URL = "https://api.stratz.com/graphql"

# Stratz API keys for enrichment
STRATZ_API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

# Time range
DAYS_BACK = 180  # 6 months


def fetch_opendota_pro_matches(days_back: int = 180) -> List[Dict]:
    """Fetch pro match IDs from OpenDota (free, no API key)"""
    
    print(f"\n🔍 Fetching pro matches from OpenDota (last {days_back} days)...")
    
    # OpenDota pro matches endpoint
    url = f"{OPENDOTA_API}/proMatches"
    
    all_matches = []
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                matches = response.json()
                
                # Filter by date
                cutoff_time = int((datetime.now() - timedelta(days=days_back)).timestamp())
                recent_matches = [m for m in matches if m.get('start_time', 0) >= cutoff_time]
                
                print(f"   ✓ Found {len(recent_matches)} pro matches")
                return recent_matches
            else:
                print(f"   ⚠️  HTTP {response.status_code} (attempt {attempt+1}/{max_attempts})")
                time.sleep(2)
                
        except Exception as e:
            print(f"   ❌ Error: {e} (attempt {attempt+1}/{max_attempts})")
            time.sleep(2)
    
    return []


def fetch_match_details_opendota(match_id: int) -> Optional[Dict]:
    """Fetch full match details from OpenDota"""
    
    url = f"{OPENDOTA_API}/matches/{match_id}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        
    except Exception as e:
        pass
    
    return None


def enrich_with_stratz(match_id: int, scraper, api_key: str) -> Optional[Dict]:
    """Get role data from Stratz"""
    
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
        "authorization": f"bearer {api_key}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    try:
        response = scraper.post(
            STRATZ_API_URL,
            json={"query": query, "variables": {"id": match_id}},
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "match" in data["data"] and data["data"]["match"]:
                return data["data"]["match"]
    except:
        pass
    
    return None


def parse_match_data(opendota_match: Dict, stratz_data: Optional[Dict] = None) -> Dict:
    """Parse match data from OpenDota (and optionally Stratz) into our format"""
    
    # Position mapping
    position_to_role = {
        1: "carry",
        2: "mid",
        3: "offlane",
        4: "softsupport",
        5: "hardsupport"
    }
    
    # Parse players from OpenDota
    radiant_roles = []
    dire_roles = []
    
    for player in opendota_match.get("players", []):
        hero_id = player.get("hero_id")
        is_radiant = player.get("isRadiant", player.get("player_slot", 0) < 128)
        
        # Try to get role from position
        lane_role = player.get("lane_role")
        if lane_role:
            role_map = {
                1: "carry",
                2: "mid",
                3: "offlane",
                4: "softsupport",
                5: "hardsupport"
            }
            role = role_map.get(lane_role, "unknown")
        else:
            # Fallback to position
            pos = player.get("position")
            role = position_to_role.get(pos, "unknown")
        
        entry = {"heroId": hero_id, "role": role}
        
        if is_radiant:
            radiant_roles.append(entry)
        else:
            dire_roles.append(entry)
    
    # If we have Stratz data, use its roles (more accurate)
    if stratz_data and "players" in stratz_data:
        radiant_roles = []
        dire_roles = []
        
        for player in stratz_data["players"]:
            pos = player.get("position")
            role = position_to_role.get(pos, player.get("role", "unknown"))
            
            entry = {"heroId": player.get("heroId"), "role": role}
            
            if player.get("isRadiant"):
                radiant_roles.append(entry)
            else:
                dire_roles.append(entry)
    
    # Get league info
    league_id = opendota_match.get("leagueid")
    league_name = opendota_match.get("league_name")
    league_tier = None
    
    if stratz_data and stratz_data.get("league"):
        league_name = stratz_data["league"].get("displayName") or league_name
        league_tier = stratz_data["league"].get("tier")
    
    return {
        "radiantWin": opendota_match.get("radiant_win", False),
        "radiantRoles": radiant_roles,
        "direRoles": dire_roles,
        "leagueId": league_id,
        "leagueName": league_name,
        "leagueTier": league_tier
    }


def main():
    import sys
    
    print("=" * 70)
    print("Fetch Pro Matches - OpenDota + Stratz Hybrid Approach")
    print("=" * 70)
    
    print("\n📝 Strategy:")
    print("   1. Get match IDs from OpenDota (free, no auth)")
    print("   2. Get match details from OpenDota (heroes, basic info)")
    print("   3. Optionally enrich with Stratz (roles, tier)")
    
    # Step 1: Get match IDs from OpenDota
    opendota_matches = fetch_opendota_pro_matches(DAYS_BACK)
    
    if not opendota_matches:
        print("\n❌ Failed to fetch matches from OpenDota")
        sys.exit(1)
    
    print(f"\n📊 Found {len(opendota_matches)} pro matches")
    
    # Ask user if they want Stratz enrichment
    print(f"\n🤔 Do you want to enrich with Stratz data?")
    print("   YES: Get accurate roles and tier (requires API keys, slower)")
    print("   NO:  Use OpenDota data only (faster, but less accurate roles)")
    
    use_stratz = False
    if STRATZ_API_KEYS[0] != "YOUR_API_KEY_1":
        print("\n   Stratz API keys detected - will enrich with Stratz data")
        use_stratz = True
    else:
        print("\n   No Stratz keys - using OpenDota data only")
    
    # Process matches
    all_matches = {}
    processed = 0
    enriched = 0
    
    if use_stratz:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )
        current_key_idx = 0
    
    print(f"\n📥 Processing matches...")
    
    for od_match in opendota_matches:
        match_id = od_match.get("match_id")
        
        if not match_id:
            continue
        
        # Get full details from OpenDota
        od_details = fetch_match_details_opendota(match_id)
        
        if not od_details:
            continue
        
        # Optionally enrich with Stratz
        stratz_data = None
        if use_stratz:
            stratz_data = enrich_with_stratz(
                match_id,
                scraper,
                STRATZ_API_KEYS[current_key_idx]
            )
            
            if stratz_data:
                enriched += 1
            
            # Rotate keys
            current_key_idx = (current_key_idx + 1) % len(STRATZ_API_KEYS)
            time.sleep(0.1)  # Small delay
        
        # Parse and store
        parsed = parse_match_data(od_details, stratz_data)
        all_matches[str(match_id)] = parsed
        
        processed += 1
        
        if processed % 100 == 0:
            if use_stratz:
                print(f"   Progress: {processed}/{len(opendota_matches)} | {enriched} enriched with Stratz")
            else:
                print(f"   Progress: {processed}/{len(opendota_matches)}")
    
    print(f"\n✅ Processed {len(all_matches)} matches")
    if use_stratz:
        print(f"   {enriched} enriched with Stratz data")
    
    # Save
    output_file = f"pro_matches_6months_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"✓ Saved {len(all_matches)} matches")
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Output: {output_file}")
    print("\n📊 Data included:")
    print("   ✓ Heroes (radiant/dire)")
    print("   ✓ Roles (from OpenDota positions" + (" + Stratz" if use_stratz else "") + ")")
    print("   ✓ League name")
    if use_stratz:
        print(f"   ✓ League tier (for {enriched} matches)")


if __name__ == "__main__":
    main()
