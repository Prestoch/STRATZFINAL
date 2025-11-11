#!/usr/bin/env python3
"""
Fetch LARGE VOLUME of recent high-quality Dota 2 matches
Combines: Pro matches + High MMR pub games

Uses OpenDota (free, unlimited) for discovery
Then enriches with Stratz for roles/tier data

Strategy:
1. Get pro matches from OpenDota (last 6 months)
2. Get high MMR pub matches from top players
3. Enrich all with Stratz data
4. Result: THOUSANDS of high-quality matches

No pip install needed for OpenDota part!
For Stratz enrichment: pip install cloudscraper
"""

import json
import time
import requests
import cloudscraper
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

OPENDOTA_API = "https://api.opendota.com/api"
STRATZ_API_URL = "https://api.stratz.com/graphql"

# Stratz API keys (for enrichment - optional but recommended)
STRATZ_API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

# Configuration
MONTHS_BACK = 6
MAX_MATCHES = 10000  # Target number of matches

# Top leaderboard players (high MMR, active)
# These play DAILY and show ALL matches
TOP_LEADERBOARD_PLAYERS = [
    111620041,   # Active leaderboard
    86745912,    # RTZ
    88719902,    # Miracle
    # Add more from https://www.opendota.com/players
]


def fetch_opendota_pro_matches(months_back: int = 6) -> List[Dict]:
    """Get ALL pro matches from OpenDota (last N months)"""
    
    print(f"\n📋 Fetching pro matches from OpenDota...")
    
    url = f"{OPENDOTA_API}/proMatches"
    cutoff_time = int((datetime.now() - timedelta(days=months_back * 30)).timestamp())
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            all_matches = response.json()
            recent = [m for m in all_matches if m.get('start_time', 0) >= cutoff_time]
            print(f"   ✓ Found {len(recent)} pro matches")
            return recent
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return []


def fetch_player_matches_opendota(account_id: int, limit: int = 100) -> List[Dict]:
    """Get recent matches for a player from OpenDota"""
    
    url = f"{OPENDOTA_API}/players/{account_id}/matches"
    params = {"limit": limit}
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    return []


def fetch_high_skill_matches(limit: int = 100) -> List[Dict]:
    """Get recent high skill pub matches from OpenDota"""
    
    print(f"\n🎮 Fetching high skill pub matches...")
    
    url = f"{OPENDOTA_API}/publicMatches"
    params = {
        "min_mmr": 6000,  # High MMR only
        "limit": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            matches = response.json()
            print(f"   ✓ Found {len(matches)} high MMR pub matches")
            return matches
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return []


def enrich_with_stratz(match_id: int, scraper, api_key: str) -> Optional[Dict]:
    """Get detailed data from Stratz (roles, tier)"""
    
    query = """
    query GetMatch($id: Long!) {
        match(id: $id) {
            id
            leagueId
            league {
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


def parse_match_opendota(match: Dict, stratz_data: Optional[Dict] = None) -> Dict:
    """Parse OpenDota match into our format"""
    
    # Position mapping
    position_map = {
        "POSITION_1": "carry",
        "POSITION_2": "mid",
        "POSITION_3": "offlane",
        "POSITION_4": "softsupport",
        "POSITION_5": "hardsupport",
        1: "carry",
        2: "mid",
        3: "offlane",
        4: "softsupport",
        5: "hardsupport"
    }
    
    # Try to get player data from match
    radiant_roles = []
    dire_roles = []
    
    # If we have Stratz data, use it (most accurate)
    if stratz_data and "players" in stratz_data:
        for player in stratz_data["players"]:
            pos = player.get("position")
            role = position_map.get(pos, "unknown")
            
            entry = {"heroId": player.get("heroId"), "role": role}
            
            if player.get("isRadiant"):
                radiant_roles.append(entry)
            else:
                dire_roles.append(entry)
    
    # Otherwise use OpenDota data
    elif "players" in match:
        for player in match.get("players", []):
            hero_id = player.get("hero_id")
            is_radiant = player.get("player_slot", 0) < 128
            
            # Try to infer role from lane
            lane = player.get("lane_role", 0)
            role = position_map.get(lane, "unknown")
            
            entry = {"heroId": hero_id, "role": role}
            
            if is_radiant:
                radiant_roles.append(entry)
            else:
                dire_roles.append(entry)
    
    # Get league info
    league_id = match.get("leagueid") or match.get("league_id")
    league_name = match.get("league_name")
    league_tier = None
    
    if stratz_data and stratz_data.get("league"):
        league_name = stratz_data["league"].get("displayName") or league_name
        league_tier = stratz_data["league"].get("tier")
    
    return {
        "radiantWin": match.get("radiant_win", False),
        "radiantRoles": radiant_roles,
        "direRoles": dire_roles,
        "leagueId": league_id,
        "leagueName": league_name,
        "leagueTier": league_tier
    }


def main():
    import sys
    
    print("=" * 70)
    print("Fetch LARGE VOLUME of High-Quality Dota 2 Matches")
    print("=" * 70)
    
    print(f"\n🎯 Goal: {MAX_MATCHES:,} recent high-quality matches")
    print(f"📅 Time range: Last {MONTHS_BACK} months")
    
    use_stratz_enrichment = STRATZ_API_KEYS[0] != "YOUR_API_KEY_1"
    
    if use_stratz_enrichment:
        print(f"✅ Stratz enrichment: ENABLED (roles + tier)")
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
        )
        current_key = 0
    else:
        print(f"⚠️  Stratz enrichment: DISABLED (add API keys for roles/tier)")
        scraper = None
    
    all_matches = {}
    match_ids_seen: Set[int] = set()
    
    # Step 1: Get PRO matches from OpenDota
    print(f"\n{'='*70}")
    print("STEP 1: Pro Matches from OpenDota")
    print("="*70)
    
    pro_matches = fetch_opendota_pro_matches(MONTHS_BACK)
    
    for pm in pro_matches:
        match_id = pm.get("match_id")
        if match_id and match_id not in match_ids_seen:
            match_ids_seen.add(match_id)
    
    print(f"   Total unique pro match IDs: {len(match_ids_seen)}")
    
    # Step 2: Get HIGH MMR pub matches from top players
    if len(match_ids_seen) < MAX_MATCHES:
        print(f"\n{'='*70}")
        print("STEP 2: High MMR Pub Matches from Top Players")
        print("="*70)
        
        # You can add MANY more player IDs here from OpenDota leaderboard
        # https://www.opendota.com/players
        for player_id in TOP_LEADERBOARD_PLAYERS:
            if len(match_ids_seen) >= MAX_MATCHES:
                break
            
            print(f"   Player {player_id}...", end=" ")
            player_matches = fetch_player_matches_opendota(player_id, limit=100)
            
            new_matches = 0
            for pm in player_matches:
                match_id = pm.get("match_id")
                if match_id and match_id not in match_ids_seen:
                    match_ids_seen.add(match_id)
                    new_matches += 1
            
            print(f"✓ {new_matches} new matches (total: {len(match_ids_seen)})")
            time.sleep(1)  # Be nice to OpenDota
    
    # Step 3: Get public high MMR matches
    if len(match_ids_seen) < MAX_MATCHES:
        print(f"\n{'='*70}")
        print("STEP 3: Public High MMR Matches")
        print("="*70)
        
        high_mmr = fetch_high_skill_matches(limit=1000)
        for pm in high_mmr:
            match_id = pm.get("match_id")
            if match_id and match_id not in match_ids_seen:
                match_ids_seen.add(match_id)
    
    print(f"\n✅ Total unique matches discovered: {len(match_ids_seen):,}")
    
    # Step 4: Get full match details
    print(f"\n{'='*70}")
    print("STEP 4: Fetching Full Match Details")
    print("="*70)
    
    match_ids_list = list(match_ids_seen)[:MAX_MATCHES]  # Limit to target
    
    print(f"   Processing {len(match_ids_list):,} matches...")
    
    processed = 0
    successful = 0
    enriched = 0
    
    for match_id in match_ids_list:
        # Get details from OpenDota
        try:
            detail_url = f"{OPENDOTA_API}/matches/{match_id}"
            response = requests.get(detail_url, timeout=15)
            
            if response.status_code == 200:
                od_data = response.json()
                
                # Optionally enrich with Stratz
                stratz_data = None
                if use_stratz_enrichment and scraper:
                    stratz_data = enrich_with_stratz(
                        match_id,
                        scraper,
                        STRATZ_API_KEYS[current_key]
                    )
                    if stratz_data:
                        enriched += 1
                    current_key = (current_key + 1) % len(STRATZ_API_KEYS)
                    time.sleep(0.05)
                
                # Parse and store
                parsed = parse_match_opendota(od_data, stratz_data)
                all_matches[str(match_id)] = parsed
                successful += 1
                
        except Exception as e:
            pass
        
        processed += 1
        
        if processed % 500 == 0:
            percent = 100 * processed / len(match_ids_list)
            print(f"   Progress: {processed:,}/{len(match_ids_list):,} ({percent:.1f}%) | {successful:,} successful | {enriched:,} enriched")
    
    print(f"\n✅ Successfully processed {successful:,} matches")
    if use_stratz_enrichment:
        print(f"   {enriched:,} enriched with Stratz data")
    
    # Save
    output_file = f"dota2_matches_{MONTHS_BACK}months_{datetime.now().strftime('%Y%m%d')}.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(all_matches, f, indent=2)
    
    print(f"✓ Saved {len(all_matches):,} matches!")
    
    # Stats
    print(f"\n📊 Final Statistics:")
    print(f"   Total matches: {len(all_matches):,}")
    pro_count = sum(1 for m in all_matches.values() if m.get('leagueId'))
    pub_count = len(all_matches) - pro_count
    print(f"   Pro matches: {pro_count:,}")
    print(f"   High MMR pubs: {pub_count:,}")
    
    if enriched > 0:
        print(f"   Stratz enriched: {enriched:,} ({100*enriched/len(all_matches):.1f}%)")
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Output: {output_file}")
    print("\n💡 To get more matches:")
    print("   - Increase MAX_MATCHES")
    print("   - Add more player IDs to TOP_LEADERBOARD_PLAYERS")
    print("   - Increase MONTHS_BACK")


if __name__ == "__main__":
    main()
