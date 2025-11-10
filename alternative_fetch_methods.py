#!/usr/bin/env python3
"""
Alternative methods to fetch Stratz data if GraphQL isn't working

Try these different approaches to see which one works with your API keys.
"""

import json
import requests
import sys

# Add your API key here
API_KEY = "YOUR_API_KEY_HERE"

def method_1_graphql_with_bearer():
    """Standard GraphQL with Bearer token (this is what we tried)"""
    print("Method 1: GraphQL with Bearer token")
    print("-" * 50)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    query = """
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
    """
    
    try:
        response = requests.post(
            url,
            json={"query": query, "variables": {"id": 6449050893}},
            headers=headers,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def method_2_graphql_with_header():
    """GraphQL with X-Api-Key header instead of Bearer"""
    print("\nMethod 2: GraphQL with X-Api-Key header")
    print("-" * 50)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    query = """
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
    """
    
    try:
        response = requests.post(
            url,
            json={"query": query, "variables": {"id": 6449050893}},
            headers=headers,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def method_3_rest_api_v1():
    """Try REST API v1 endpoint"""
    print("\nMethod 3: REST API v1")
    print("-" * 50)
    
    url = f"https://api.stratz.com/api/v1/match/6449050893"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def method_4_rest_api_v2():
    """Try REST API v2 endpoint"""
    print("\nMethod 4: REST API v2")
    print("-" * 50)
    
    url = f"https://api.stratz.com/api/v2/match/6449050893"
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def method_5_api_key_in_url():
    """Try API key as URL parameter"""
    print("\nMethod 5: API key in URL parameter")
    print("-" * 50)
    
    url = f"https://api.stratz.com/api/match/6449050893?api_key={API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def method_6_check_api_status():
    """Check if there's a status or info endpoint"""
    print("\nMethod 6: Check API status/info")
    print("-" * 50)
    
    urls_to_try = [
        "https://api.stratz.com/",
        "https://api.stratz.com/api",
        "https://api.stratz.com/status",
        "https://api.stratz.com/health"
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=5)
            print(f"{url}: {response.status_code}")
            if response.status_code == 200:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"{url}: Error - {e}")


def method_7_opendota_crosscheck():
    """Check if OpenDota has league info as alternative"""
    print("\nMethod 7: OpenDota API (alternative source)")
    print("-" * 50)
    
    url = "https://api.opendota.com/api/matches/6449050893"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Has league_id: {'league_id' in data}")
            if 'league_id' in data:
                print(f"League ID: {data.get('league_id')}")
                print(f"League name: {data.get('league', {}).get('name')}")
                print(f"League tier: {data.get('league', {}).get('tier')}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Test all methods"""
    print("=" * 60)
    print("Testing Different API Access Methods")
    print("=" * 60)
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ Please add your API key at the top of this script!")
        sys.exit(1)
    
    print(f"\nUsing API key: {API_KEY[:12]}...{API_KEY[-4:]}")
    print()
    
    methods = [
        method_1_graphql_with_bearer,
        method_2_graphql_with_header,
        method_3_rest_api_v1,
        method_4_rest_api_v2,
        method_5_api_key_in_url,
        method_6_check_api_status,
        method_7_opendota_crosscheck
    ]
    
    results = []
    for method in methods:
        try:
            success = method()
            results.append((method.__name__, success))
        except Exception as e:
            print(f"Unexpected error in {method.__name__}: {e}")
            results.append((method.__name__, False))
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{status} - {name}")
    
    working = [name for name, success in results if success]
    if working:
        print(f"\n✅ Found {len(working)} working method(s)!")
        print("We can update the main script to use the working method.")
    else:
        print("\n⚠️  No methods worked automatically.")
        print("Next steps:")
        print("1. Check Stratz website's Network tab (see inspect_stratz_api.md)")
        print("2. Or try the Chrome console script (stratz_console_fetch.js)")


if __name__ == "__main__":
    main()
