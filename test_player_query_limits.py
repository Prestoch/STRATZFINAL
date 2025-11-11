#!/usr/bin/env python3
"""
Test the limits of player.matches() query:
- How many matches can we fetch?
- Can we paginate (skip/take)?
- How far back does the data go?
- Can we filter by date range?
"""

import cloudscraper
import json
from datetime import datetime, timedelta

API_KEY = "YOUR_API_KEY_HERE"
STRATZ_API_URL = "https://api.stratz.com/graphql"

def test_player_matches(steam_id: int, take: int, skip: int = 0, test_name: str = ""):
    """Test player matches query with different parameters"""
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
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
            "skip": skip
        }
    }
    
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Steam ID: {steam_id}")
    print(f"Take: {take}, Skip: {skip}")
    
    try:
        response = scraper.post(
            STRATZ_API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Errors: {data['errors']}")
            return None
        
        if "data" in data and "player" in data["data"]:
            matches = data["data"]["player"].get("matches", [])
            
            if len(matches) > 0:
                print(f"✅ Got {len(matches)} matches")
                
                # Show date range
                dates = [m.get("startDateTime") for m in matches if m.get("startDateTime")]
                if dates:
                    oldest = datetime.fromtimestamp(min(dates))
                    newest = datetime.fromtimestamp(max(dates))
                    print(f"   Oldest: {oldest.strftime('%Y-%m-%d %H:%M')}")
                    print(f"   Newest: {newest.strftime('%Y-%m-%d %H:%M')}")
                    print(f"   Range: {(newest - oldest).days} days")
                
                # Show pro matches
                pro_matches = [m for m in matches if m.get("leagueId") and m.get("leagueId") > 0]
                print(f"   Pro matches: {len(pro_matches)}/{len(matches)}")
                
                # Show sample
                print(f"\n   Sample (first 3):")
                for m in matches[:3]:
                    date = datetime.fromtimestamp(m.get("startDateTime", 0))
                    league = m.get("leagueId", 0)
                    print(f"     • Match {m['id']}: {date.strftime('%Y-%m-%d')} | League: {league}")
                
                return matches
            else:
                print(f"⚠️  No matches returned")
                return []
        
        print(f"❌ Unexpected response structure")
        return None
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


def test_with_time_filter(steam_id: int, start_time: int, end_time: int):
    """Test if we can filter by time range"""
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    query = """
    query GetPlayerMatches($steamAccountId: Long!, $request: PlayerMatchesRequestType!) {
        player(steamAccountId: $steamAccountId) {
            matches(request: $request) {
                id
                startDateTime
            }
        }
    }
    """
    
    variables = {
        "steamAccountId": steam_id,
        "request": {
            "take": 50,
            "startDateTime": start_time,
            "endDateTime": end_time
        }
    }
    
    print(f"\n{'='*70}")
    print(f"TEST: Time Range Filter")
    print(f"{'='*70}")
    print(f"Start: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d')}")
    print(f"End: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d')}")
    
    try:
        response = scraper.post(
            STRATZ_API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}")
            return False
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Time filter not supported or error:")
            for error in data['errors']:
                print(f"   • {error.get('message')}")
            return False
        
        if "data" in data:
            print(f"✅ Time filter works!")
            matches = data["data"]["player"].get("matches", [])
            print(f"   Got {len(matches)} matches in date range")
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    import sys
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set API_KEY!")
        sys.exit(1)
    
    print("="*70)
    print("PLAYER MATCHES QUERY - LIMITS & CAPABILITIES TEST")
    print("="*70)
    
    # Use Dendi as test subject (active pro player)
    test_steam_id = 111620041  # Dendi
    
    print(f"\nTest subject: Steam ID {test_steam_id}")
    
    # Test 1: Default (small take)
    test_player_matches(test_steam_id, take=20, skip=0, test_name="1. Default Query (take=20)")
    
    # Test 2: Large take
    test_player_matches(test_steam_id, take=100, skip=0, test_name="2. Large Query (take=100)")
    
    # Test 3: Very large take
    test_player_matches(test_steam_id, take=500, skip=0, test_name="3. Very Large Query (take=500)")
    
    # Test 4: Maximum take
    test_player_matches(test_steam_id, take=1000, skip=0, test_name="4. Max Query (take=1000)")
    
    # Test 5: Pagination - second page
    test_player_matches(test_steam_id, take=100, skip=100, test_name="5. Pagination (skip=100, take=100)")
    
    # Test 6: Pagination - far skip
    test_player_matches(test_steam_id, take=100, skip=500, test_name="6. Deep Pagination (skip=500, take=100)")
    
    # Test 7: Time range filter
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=180)).timestamp())  # 6 months
    test_with_time_filter(test_steam_id, start_time, end_time)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*70)
    
    print("\n📊 Based on tests above:")
    print("\n1. MAXIMUM MATCHES PER QUERY:")
    print("   Check 'take=1000' test above")
    print("   Stratz might limit to 100-500 matches per request")
    
    print("\n2. PAGINATION:")
    print("   Check if skip/take work for getting more matches")
    print("   If skip=100 works, we can paginate through ALL matches")
    
    print("\n3. DATE RANGE:")
    print("   Check if time filters are supported")
    print("   If yes, we can efficiently get 6-month matches")
    
    print("\n4. DATA AVAILABILITY:")
    print("   Check oldest match date in results")
    print("   Stratz typically stores years of data")
    
    print("\n" + "="*70)
    print("STRATEGY FOR 6 MONTHS OF DATA")
    print("="*70)
    
    print("\nIf pagination works (skip/take):")
    print("  → Loop: take=100, skip=0, 100, 200, 300...")
    print("  → Stop when matches are older than 6 months")
    print("  → Can get ALL matches for a player")
    
    print("\nIf time filter works (startDateTime/endDateTime):")
    print("  → Single query with date range")
    print("  → More efficient!")
    
    print("\nIf neither works:")
    print("  → Limited to most recent ~100-500 matches")
    print("  → Need more pro players to get coverage")
    
    print("\n💡 Run this test to see what's possible!")


if __name__ == "__main__":
    main()
