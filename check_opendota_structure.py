#!/usr/bin/env python3
"""
Quick check to see what data OpenDota provides for pro matches
"""

import requests
import json

print("Checking OpenDota API structure...")
print("=" * 70)

# Get recent pro matches
url = "https://api.opendota.com/api/proMatches"
response = requests.get(url, timeout=30)

if response.status_code == 200:
    matches = response.json()
    
    print(f"\n✓ Found {len(matches)} recent pro matches\n")
    
    # Show first 5 matches
    print("Sample matches (first 5):\n")
    
    for i, match in enumerate(matches[:5]):
        print(f"Match {i+1}:")
        print(f"  match_id: {match.get('match_id')}")
        print(f"  league_name: {match.get('league_name')}")
        print(f"  leagueid: {match.get('leagueid')}")
        print(f"  radiant_win: {match.get('radiant_win')}")
        print(f"  start_time: {match.get('start_time')}")
        print(f"  radiant_team: {match.get('radiant_name')}")
        print(f"  dire_team: {match.get('dire_name')}")
        print()
    
    # Check all unique league names
    print("\n" + "=" * 70)
    print("All unique league names from recent matches:")
    print("=" * 70)
    
    league_names = set()
    for match in matches[:100]:  # Check first 100
        name = match.get('league_name')
        if name:
            league_names.add(name)
    
    for name in sorted(league_names):
        print(f"  • {name}")
    
    print(f"\n✓ Total unique leagues in sample: {len(league_names)}")
    
    # Now fetch detailed match info
    print("\n" + "=" * 70)
    print("Detailed match info example:")
    print("=" * 70)
    
    sample_match_id = matches[0]['match_id']
    detail_url = f"https://api.opendota.com/api/matches/{sample_match_id}"
    
    print(f"\nFetching details for match {sample_match_id}...")
    detail_response = requests.get(detail_url, timeout=30)
    
    if detail_response.status_code == 200:
        detail_data = detail_response.json()
        
        print("\nAvailable fields:")
        print(f"  match_id: {detail_data.get('match_id')}")
        print(f"  radiant_win: {detail_data.get('radiant_win')}")
        print(f"  duration: {detail_data.get('duration')}")
        print(f"  start_time: {detail_data.get('start_time')}")
        print(f"  leagueid: {detail_data.get('leagueid')}")
        print(f"  league_name: {detail_data.get('league_name')}")
        print(f"  league_tier: {detail_data.get('league_tier')}")  # This might exist!
        print(f"  series_id: {detail_data.get('series_id')}")
        print(f"  radiant_team: {detail_data.get('radiant_team')}")
        print(f"  dire_team: {detail_data.get('dire_team')}")
        
        print(f"\n  Number of players: {len(detail_data.get('players', []))}")
        
        if detail_data.get('players'):
            print("\n  Sample player data:")
            player = detail_data['players'][0]
            print(f"    hero_id: {player.get('hero_id')}")
            print(f"    player_slot: {player.get('player_slot')}")
            print(f"    lane_role: {player.get('lane_role')}")
            print(f"    is_roaming: {player.get('is_roaming')}")
            print(f"    kills: {player.get('kills')}")
            print(f"    deaths: {player.get('deaths')}")
            print(f"    assists: {player.get('assists')}")
        
        # Check if tier exists
        if 'league_tier' in detail_data:
            print(f"\n✓ OpenDota HAS league_tier field!")
            print(f"  Value: {detail_data.get('league_tier')}")
        else:
            print(f"\n✗ OpenDota does NOT have league_tier field")
            print(f"  (Only available from Stratz)")
        
        print("\n" + "=" * 70)
        print("Full match structure (first 2000 chars):")
        print("=" * 70)
        print(json.dumps(detail_data, indent=2)[:2000])
        print("...")
    
else:
    print(f"❌ Failed to fetch matches: HTTP {response.status_code}")

print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)
print("OpenDota provides:")
print("  ✓ leagueid (numeric)")
print("  ✓ league_name (string, e.g., 'DreamLeague Season 21')")
print("  ? league_tier (might exist, checking above)")
print("\nStratz provides:")
print("  ✓ leagueId")
print("  ✓ league.displayName") 
print("  ✓ league.tier (PREMIUM, PROFESSIONAL, etc.)")
