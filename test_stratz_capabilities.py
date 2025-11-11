#!/usr/bin/env python3
"""
Comprehensive test of Stratz API capabilities WITHOUT admin access
Tests what data we can fetch and what we cannot
"""

import cloudscraper
import json
from datetime import datetime, timedelta

API_KEY = "YOUR_API_KEY_HERE"
STRATZ_API_URL = "https://api.stratz.com/graphql"

def test_query(name: str, query: str, variables: dict = None):
    """Test a query and show what data we can get"""
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'darwin', 'mobile': False}
    )
    
    headers = {
        "authorization": f"bearer {API_KEY}",
        "content-type": "application/json",
        "origin": "https://stratz.com",
        "referer": "https://stratz.com/",
    }
    
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    try:
        response = scraper.post(
            STRATZ_API_URL,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=15
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error")
            return None
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL Errors:")
            for error in data['errors']:
                print(f"   • {error.get('message')}")
            return None
        
        if "data" in data:
            print(f"✅ SUCCESS!")
            print(f"\nData structure:")
            print(json.dumps(data['data'], indent=2)[:1000])
            if len(json.dumps(data['data'])) > 1000:
                print("   ... (truncated)")
            return data['data']
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None


def main():
    import sys
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set API_KEY!")
        sys.exit(1)
    
    print("="*70)
    print("STRATZ API CAPABILITIES TEST (No Admin Access)")
    print("="*70)
    print("\nTesting what we CAN and CANNOT fetch from Stratz...\n")
    
    results = {}
    
    # ========================================
    # TEST 1: SINGLE MATCH (Known to work)
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: SINGLE MATCH QUERIES")
    print("="*70)
    
    result = test_query(
        "1. Single Match - Full Data",
        """
        query GetMatch($id: Long!) {
            match(id: $id) {
                id
                didRadiantWin
                startDateTime
                durationSeconds
                leagueId
                league {
                    id
                    displayName
                    tier
                }
                radiantTeamId
                direTeamId
                players {
                    steamAccountId
                    heroId
                    isRadiant
                    position
                    role
                    kills
                    deaths
                    assists
                }
            }
        }
        """,
        {"id": 6449050893}
    )
    results['single_match'] = result is not None
    
    # ========================================
    # TEST 2: PLAYER QUERIES
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: PLAYER-BASED MATCH DISCOVERY")
    print("="*70)
    
    result = test_query(
        "2. Player Recent Matches",
        """
        query GetPlayerMatches($steamAccountId: Long!, $request: PlayerMatchesRequestType!) {
            player(steamAccountId: $steamAccountId) {
                steamAccountId
                matches(request: $request) {
                    id
                    leagueId
                    startDateTime
                }
            }
        }
        """,
        {
            "steamAccountId": 111620041,  # Dendi
            "request": {
                "take": 20,
                "skip": 0
            }
        }
    )
    results['player_matches'] = result is not None
    
    # Test if we can filter for pro matches
    result = test_query(
        "3. Player Pro Matches Only",
        """
        query GetPlayerProMatches($steamAccountId: Long!, $request: PlayerMatchesRequestType!) {
            player(steamAccountId: $steamAccountId) {
                matches(request: $request) {
                    id
                    leagueId
                    league {
                        displayName
                        tier
                    }
                }
            }
        }
        """,
        {
            "steamAccountId": 111620041,
            "request": {
                "take": 50,
                "isPro": True  # Try pro filter
            }
        }
    )
    results['player_pro_matches'] = result is not None
    
    # ========================================
    # TEST 3: TEAM QUERIES
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: TEAM-BASED MATCH DISCOVERY")
    print("="*70)
    
    result = test_query(
        "4. Team Recent Matches",
        """
        query GetTeamMatches($teamId: Int!, $request: TeamMatchesRequestType!) {
            team(teamId: $teamId) {
                id
                name
                matches(request: $request) {
                    id
                    leagueId
                    league {
                        tier
                    }
                }
            }
        }
        """,
        {
            "teamId": 2586976,  # OG
            "request": {
                "take": 20
            }
        }
    )
    results['team_matches'] = result is not None
    
    # ========================================
    # TEST 4: HERO QUERIES
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: HERO-BASED MATCH DISCOVERY")
    print("="*70)
    
    result = test_query(
        "5. Hero Recent Matches",
        """
        query GetHeroMatches($heroId: Short!) {
            heroStats {
                heroVsHeroMatchup(heroId: $heroId, take: 10) {
                    matchCount
                }
            }
        }
        """,
        {"heroId": 1}
    )
    results['hero_matches'] = result is not None
    
    # ========================================
    # TEST 5: LEAGUE QUERIES
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: LEAGUE-BASED DISCOVERY")
    print("="*70)
    
    # Try getting list of all leagues
    result = test_query(
        "6. Get All Active Leagues",
        """
        query GetLeagues {
            leagues {
                id
                displayName
                tier
            }
        }
        """
    )
    results['leagues_list'] = result is not None
    
    # Try with time filter
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=30)).timestamp())
    
    result = test_query(
        "7. Leagues in Time Range",
        """
        query GetLeaguesFiltered($request: LeagueRequestType!) {
            leagues(request: $request) {
                id
                displayName
                tier
            }
        }
        """,
        {
            "request": {
                "startDateTime": start_time,
                "endDateTime": end_time
            }
        }
    )
    results['leagues_filtered'] = result is not None
    
    # Try getting matches from a known league
    result = test_query(
        "8. League Matches",
        """
        query GetLeagueMatches($leagueId: Int!, $request: LeagueMatchesRequestType!) {
            league(id: $leagueId) {
                id
                displayName
                matches(request: $request) {
                    id
                    startDateTime
                }
            }
        }
        """,
        {
            "leagueId": 15728,  # A known league
            "request": {
                "take": 20
            }
        }
    )
    results['league_matches'] = result is not None
    
    # ========================================
    # TEST 6: SEARCH/FEED QUERIES
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: MATCH FEED/SEARCH")
    print("="*70)
    
    result = test_query(
        "9. Pro Match Feed",
        """
        query GetProMatches {
            proMatches(take: 20) {
                id
                leagueId
            }
        }
        """
    )
    results['pro_match_feed'] = result is not None
    
    result = test_query(
        "10. Live Pro Matches",
        """
        query GetLiveMatches {
            live {
                matches {
                    matchId
                    leagueId
                    gameState
                }
            }
        }
        """
    )
    results['live_matches'] = result is not None
    
    # ========================================
    # TEST 7: CONSTANTS/META
    # ========================================
    print("\n" + "="*70)
    print("CATEGORY: CONSTANTS/METADATA")
    print("="*70)
    
    result = test_query(
        "11. Get All Heroes",
        """
        query GetHeroes {
            constants {
                heroes {
                    id
                    displayName
                }
            }
        }
        """
    )
    results['heroes_list'] = result is not None
    
    result = test_query(
        "12. Get All Leagues (via constants)",
        """
        query GetLeaguesConstants {
            constants {
                leagues {
                    id
                    displayName
                    tier
                }
            }
        }
        """
    )
    results['leagues_constants'] = result is not None
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*70)
    print("SUMMARY: WHAT WE CAN ACCESS")
    print("="*70)
    
    print("\n✅ WORKING (Can fetch data):")
    for key, works in results.items():
        if works:
            print(f"   ✓ {key.replace('_', ' ').title()}")
    
    print("\n❌ NOT WORKING (Requires admin or doesn't exist):")
    for key, works in results.items():
        if not works:
            print(f"   ✗ {key.replace('_', ' ').title()}")
    
    print("\n" + "="*70)
    print("DATA AVAILABILITY SUMMARY")
    print("="*70)
    
    print("\nWhat we CAN get from Stratz:")
    if results.get('single_match'):
        print("  ✅ Match IDs (if we already have them)")
        print("  ✅ League IDs (from match data)")
        print("  ✅ League Names (from match data)")
        print("  ✅ League Tier (PREMIUM, PROFESSIONAL, etc.)")
        print("  ✅ Heroes (from match data)")
        print("  ✅ Hero Roles (position/role from match data)")
    
    if results.get('player_matches'):
        print("  ✅ Match IDs (from player query - DISCOVERY METHOD!)")
    
    if results.get('team_matches'):
        print("  ✅ Match IDs (from team query - DISCOVERY METHOD!)")
    
    if results.get('league_matches'):
        print("  ✅ Match IDs (from league query - DISCOVERY METHOD!)")
    
    print("\n" + "="*70)
    print("RECOMMENDATION")
    print("="*70)
    
    if results.get('player_matches') or results.get('team_matches') or results.get('league_matches'):
        print("\n🎉 GOOD NEWS! We CAN discover match IDs from Stratz!")
        print("\nWorking methods:")
        if results.get('player_matches'):
            print("  • Query top pro players' recent matches")
        if results.get('team_matches'):
            print("  • Query pro teams' recent matches")
        if results.get('league_matches'):
            print("  • Query leagues for their matches")
        print("\nWe can build a fetcher using these methods!")
    else:
        print("\n⚠️  Cannot discover new match IDs from Stratz")
        print("Must use OpenDota for discovery, then enrich with Stratz")


if __name__ == "__main__":
    main()
