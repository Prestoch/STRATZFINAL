#!/usr/bin/env python3
"""
Test alternative match discovery methods:
1. Can we query by rank/MMR?
2. Can we get recent matches globally?
3. Can we query by team instead of player?
4. Can we get high-level pub matches?
"""

import cloudscraper
import json
from datetime import datetime, timedelta

API_KEY = "YOUR_API_KEY_HERE"
STRATZ_API_URL = "https://api.stratz.com/graphql"

def test_query(name: str, query: str, variables: dict = None):
    """Test a query"""
    
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
            return False
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ Errors:")
            for error in data['errors']:
                print(f"   • {error.get('message')}")
            return False
        
        if "data" in data:
            print(f"✅ SUCCESS!")
            # Show data structure
            def show_structure(obj, indent=0):
                if isinstance(obj, dict):
                    for key, value in list(obj.items())[:5]:  # First 5 keys
                        if isinstance(value, list) and len(value) > 0:
                            print("  " * indent + f"{key}: [{len(value)} items]")
                            if len(value) > 0:
                                show_structure(value[0], indent + 1)
                        elif isinstance(value, dict):
                            print("  " * indent + f"{key}:")
                            show_structure(value, indent + 1)
                        else:
                            print("  " * indent + f"{key}: {value}")
                elif isinstance(obj, list) and len(obj) > 0:
                    show_structure(obj[0], indent)
            
            show_structure(data['data'])
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
    print("ALTERNATIVE MATCH DISCOVERY METHODS")
    print("="*70)
    
    results = {}
    
    # TEST 1: Team matches (maybe better than player?)
    results['team_matches'] = test_query(
        "1. Team Matches (OG)",
        """
        query GetTeamMatches($teamId: Int!, $request: TeamMatchesRequestType!) {
            team(teamId: $teamId) {
                id
                name
                matches(request: $request) {
                    id
                    leagueId
                    startDateTime
                }
            }
        }
        """,
        {
            "teamId": 2586976,  # OG
            "request": {"take": 50}
        }
    )
    
    # TEST 2: Stratz leaderboard
    results['leaderboard'] = test_query(
        "2. Stratz Leaderboard Players",
        """
        query GetLeaderboard($request: PlayerLeaderBoardRequestType!) {
            leaderboard {
                players(request: $request) {
                    steamAccountId
                    rank
                }
            }
        }
        """,
        {
            "request": {
                "take": 50,
                "skip": 0
            }
        }
    )
    
    # TEST 3: High MMR matches
    results['high_mmr'] = test_query(
        "3. High MMR/Rank Matches",
        """
        query GetHighRankMatches {
            matches(rankBracket: IMMORTAL, take: 20) {
                id
                averageRank
            }
        }
        """
    )
    
    # TEST 4: Recent matches feed
    results['recent_feed'] = test_query(
        "4. Recent Matches Feed",
        """
        query GetRecentMatches($take: Int!) {
            recentMatches(take: $take) {
                id
                leagueId
            }
        }
        """,
        {"take": 20}
    )
    
    # TEST 5: Matches by hero (to discover IDs)
    results['hero_matches'] = test_query(
        "5. Recent Matches by Hero",
        """
        query GetHeroMatches($heroId: Short!, $take: Int!) {
            hero(heroId: $heroId) {
                id
                matches(take: $take) {
                    id
                    leagueId
                }
            }
        }
        """,
        {"heroId": 1, "take": 20}
    )
    
    # TEST 6: Live leaderboard matches
    results['live_leaderboard'] = test_query(
        "6. Live Leaderboard Matches",
        """
        query GetLiveLeaderboard {
            live {
                leaderboardMatches {
                    matchId
                    averageRank
                }
            }
        }
        """
    )
    
    # TEST 7: Player by rank query
    results['player_by_rank'] = test_query(
        "7. Players by Rank",
        """
        query GetTopPlayers {
            players(request: {orderBy: RANK, take: 50}) {
                steamAccountId
                steamAccount {
                    seasonRank
                }
            }
        }
        """
    )
    
    # TEST 8: Match feed with filters
    results['match_feed_filtered'] = test_query(
        "8. Match Feed with Pro Filter",
        """
        query GetMatchFeed($request: MatchesRequestType!) {
            matches(request: $request) {
                id
                leagueId
            }
        }
        """,
        {
            "request": {
                "isPro": True,
                "take": 20
            }
        }
    )
    
    # SUMMARY
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    print("\n✅ WORKING:")
    for key, works in results.items():
        if works:
            print(f"   ✓ {key.replace('_', ' ').title()}")
    
    print("\n❌ NOT WORKING:")
    for key, works in results.items():
        if not works:
            print(f"   ✗ {key.replace('_', ' ').title()}")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    if results.get('team_matches'):
        print("\n🎯 TEAM QUERIES WORK!")
        print("   → Query pro teams instead of players")
        print("   → More reliable for official matches")
        print("   → Teams play in all tournaments")
    
    if results.get('leaderboard'):
        print("\n📊 LEADERBOARD ACCESS WORKS!")
        print("   → Get active high-MMR players")
        print("   → Query their matches")
        print("   → More matches than pro accounts")
    
    if results.get('live_leaderboard'):
        print("\n🔴 LIVE LEADERBOARD WORKS!")
        print("   → Shows currently playing high MMR games")
        print("   → Can track and fetch after completion")
    
    print("\n💡 KEY INSIGHT:")
    print("   Pro player accounts might only show OFFICIAL matches")
    print("   Their daily pub games are on different accounts or hidden")
    print("   For PRO match dataset: This is actually GOOD!")
    print("   You WANT official matches only (with leagueId)")
    
    print("\n🎯 BEST STRATEGIES:")
    if results.get('team_matches'):
        print("   1. Use TEAM queries (more consistent)")
    if results.get('player_matches'):
        print("   2. Query 100+ pro players (get all official matches)")
    print("   3. Official matches = what you want for analysis!")
    
    print("\n⚠️  If you want DAILY PUB GAMES:")
    print("   Those are on leaderboard accounts (different from pro accounts)")
    print("   But pub games don't have:")
    print("   - League tier")
    print("   - Official team compositions")
    print("   - Tournament context")


if __name__ == "__main__":
    main()
