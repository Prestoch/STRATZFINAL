#!/usr/bin/env python3
"""
Test different Stratz GraphQL queries to find what works WITHOUT admin access
"""

import cloudscraper
import json

API_KEY = "YOUR_API_KEY_HERE"
STRATZ_API_URL = "https://api.stratz.com/graphql"

def test_query(name: str, query: str, variables: dict = None):
    """Test a GraphQL query"""
    
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
    print(f"Query: {query[:200]}...")
    if variables:
        print(f"Variables: {json.dumps(variables, indent=2)[:200]}...")
    
    try:
        response = scraper.post(
            STRATZ_API_URL,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=15
        )
        
        print(f"\nStatus: {response.status_code}")
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ ERRORS: {json.dumps(data['errors'], indent=2)}")
            return False
        elif "data" in data:
            print(f"✅ SUCCESS!")
            print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            return True
        else:
            print(f"Unknown response: {json.dumps(data, indent=2)[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    import sys
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("❌ Please set API_KEY at the top of this script!")
        sys.exit(1)
    
    print("="*70)
    print("STRATZ QUERY DISCOVERY")
    print("="*70)
    print("Finding queries that work without admin access...")
    
    # Test 1: Single match query (we know this works)
    test_query(
        "Single Match Query (known to work)",
        """
        query GetMatch($id: Long!) {
            match(id: $id) {
                id
                leagueId
                league {
                    displayName
                    tier
                }
            }
        }
        """,
        {"id": 6449050893}
    )
    
    # Test 2: Player matches query
    test_query(
        "Player Matches Query",
        """
        query GetPlayerMatches($steamAccountId: Long!) {
            player(steamAccountId: $steamAccountId) {
                matches(request: {take: 5}) {
                    id
                    leagueId
                }
            }
        }
        """,
        {"steamAccountId": 111620041}  # Dendi's Steam ID
    )
    
    # Test 3: Search query
    test_query(
        "Search Query",
        """
        query SearchMatches($request: MatchRequestType!) {
            matches(request: $request) {
                id
                leagueId
            }
        }
        """,
        {
            "request": {
                "take": 10,
                "isPro": True
            }
        }
    )
    
    # Test 4: Constants query (should work)
    test_query(
        "Constants Query",
        """
        query {
            constants {
                heroes {
                    id
                    displayName
                }
            }
        }
        """
    )
    
    # Test 5: League by ID
    test_query(
        "Single League Query",
        """
        query GetLeague($id: Int!) {
            league(id: $id) {
                id
                displayName
                tier
                matches {
                    id
                }
            }
        }
        """,
        {"id": 14268}  # A real league ID
    )
    
    # Test 6: Stratz dashboard query (from the curl you shared)
    test_query(
        "Dashboard Upcoming Series",
        """
        query GetDashboardUpcomingProSeries($request: LeagueRequestType!) {
            leagues(request: $request) {
                id
                displayName
                tier
                nodeGroups {
                    nodes {
                        id
                        actualTime
                    }
                }
            }
        }
        """,
        {
            "request": {
                "tiers": ["MINOR", "MAJOR", "INTERNATIONAL"],
                "betweenStartDateTime": 1762707600,
                "betweenEndDateTime": 1763139600
            }
        }
    )
    
    # Test 7: Try getting live games
    test_query(
        "Live Games Query",
        """
        query GetLiveMatches {
            live {
                matches {
                    matchId
                    leagueId
                }
            }
        }
        """
    )
    
    # Test 8: Hero stats (might show recent pro matches)
    test_query(
        "Hero Stats Query",
        """
        query GetHeroStats($heroId: Short!) {
            heroStats {
                hero(heroId: $heroId) {
                    stats {
                        matchCount
                    }
                }
            }
        }
        """,
        {"heroId": 1}
    )
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("Check which queries returned ✅ SUCCESS")
    print("Those are the ones we can use to discover matches!")


if __name__ == "__main__":
    main()
