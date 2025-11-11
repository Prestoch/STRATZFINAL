#!/usr/bin/env python3
"""
Comprehensive Stratz API Diagnosis Tool

Tests various authentication methods and endpoints to figure out
what actually works with your API keys.
"""

import requests
import json
import sys

API_KEY = "YOUR_API_KEY_HERE"

# Test match ID
TEST_MATCH_ID = 6449050893

def test_1_bearer_token_graphql():
    """Test 1: GraphQL with Authorization: Bearer (what we tried)"""
    print("\n" + "="*70)
    print("TEST 1: GraphQL with Authorization: Bearer <token>")
    print("="*70)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
    
    payload = {
        "query": query,
        "variables": {"id": TEST_MATCH_ID}
    }
    
    try:
        print(f"URL: {url}")
        print(f"Headers: {json.dumps({k:v[:50]+'...' if len(v)>50 else v for k,v in headers.items()}, indent=2)}")
        print(f"Payload: {json.dumps(payload)[:200]}...")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True
        else:
            print(f"❌ FAILED with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_2_header_token():
    """Test 2: Try Authorization in different format"""
    print("\n" + "="*70)
    print("TEST 2: GraphQL with Authorization: token <token>")
    print("="*70)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "Authorization": f"token {API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    query = """
    query GetMatch($id: Long!) {
        match(id: $id) {
            id
            leagueId
        }
    }
    """
    
    try:
        response = requests.post(
            url,
            json={"query": query, "variables": {"id": TEST_MATCH_ID}},
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True
        return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_3_simple_constants():
    """Test 3: Try a simpler query (constants don't require auth)"""
    print("\n" + "="*70)
    print("TEST 3: Simple constants query (no auth required)")
    print("="*70)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    query = """
    query {
        constants {
            heroes {
                id
                displayName
            }
        }
    }
    """
    
    try:
        response = requests.post(
            url,
            json={"query": query},
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! GraphQL endpoint works without auth")
            return True
        return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_4_with_origin_header():
    """Test 4: Add Origin header (maybe CORS issue)"""
    print("\n" + "="*70)
    print("TEST 4: With Origin and Referer headers")
    print("="*70)
    
    url = "https://api.stratz.com/graphql"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Origin": "https://stratz.com",
        "Referer": "https://stratz.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    query = """
    query GetMatch($id: Long!) {
        match(id: $id) {
            id
            leagueId
        }
    }
    """
    
    try:
        response = requests.post(
            url,
            json={"query": query, "variables": {"id": TEST_MATCH_ID}},
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            return True
        return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_5_opendota():
    """Test 5: Try OpenDota as alternative"""
    print("\n" + "="*70)
    print("TEST 5: OpenDota API (alternative source)")
    print("="*70)
    
    url = f"https://api.opendota.com/api/matches/{TEST_MATCH_ID}"
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS!")
            print(f"Match ID: {data.get('match_id')}")
            print(f"League ID: {data.get('leagueid')}")
            print(f"League Name: {data.get('league_name')}")
            print(f"League Tier: {data.get('league_tier')}")
            return True
        else:
            print(f"Response: {response.text[:300]}")
        return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_6_check_api_key_format():
    """Test 6: Validate API key format"""
    print("\n" + "="*70)
    print("TEST 6: API Key Format Validation")
    print("="*70)
    
    print(f"API Key: {API_KEY[:15]}...{API_KEY[-10:]}")
    print(f"Length: {len(API_KEY)} characters")
    
    if API_KEY.startswith("eyJ"):
        print("✅ Looks like a JWT token (correct format)")
        
        # Try to decode the header
        try:
            import base64
            header = API_KEY.split('.')[0]
            # Add padding if needed
            header += '=' * (4 - len(header) % 4)
            decoded = base64.b64decode(header)
            print(f"JWT Header: {decoded.decode('utf-8')}")
        except:
            pass
    else:
        print("⚠️  Doesn't look like a JWT token")
    
    return True


def test_7_stratz_api_info():
    """Test 7: Try to get API info"""
    print("\n" + "="*70)
    print("TEST 7: Stratz API Info Endpoints")
    print("="*70)
    
    endpoints = [
        "https://api.stratz.com/",
        "https://api.stratz.com/api",
        "https://api.stratz.com/health",
        "https://api.stratz.com/status",
        "https://api.stratz.com/.well-known/openapi"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, timeout=5)
            print(f"{endpoint}: {response.status_code}")
            if response.status_code == 200:
                print(f"  Content: {response.text[:200]}")
        except Exception as e:
            print(f"{endpoint}: {str(e)[:50]}")
    
    return False


def main():
    """Run all tests"""
    print("╔" + "="*68 + "╗")
    print("║" + " "*20 + "STRATZ API DIAGNOSIS TOOL" + " "*23 + "║")
    print("╚" + "="*68 + "╝")
    
    if API_KEY == "YOUR_API_KEY_HERE":
        print("\n❌ ERROR: Please set your API key at the top of this script!")
        print("Edit the line: API_KEY = \"YOUR_API_KEY_HERE\"")
        sys.exit(1)
    
    tests = [
        test_6_check_api_key_format,
        test_3_simple_constants,
        test_1_bearer_token_graphql,
        test_2_header_token,
        test_4_with_origin_header,
        test_7_stratz_api_info,
        test_5_opendota
    ]
    
    results = []
    for test_func in tests:
        try:
            success = test_func()
            results.append((test_func.__name__, test_func.__doc__.split('\n')[0].replace('"""', ''), success))
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            results.append((test_func.__name__, test_func.__doc__.split('\n')[0].replace('"""', ''), False))
    
    # Summary
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*25 + "RESULTS SUMMARY" + " "*28 + "║")
    print("╚" + "="*68 + "╝")
    
    for name, desc, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {desc}")
    
    successful = [desc for _, desc, s in results if s]
    
    if successful:
        print(f"\n✅ Found {len(successful)} working method(s)!")
        print("\nNext step: I can update the scripts to use the working method.")
    else:
        print("\n⚠️  No methods worked.")
        print("\n📋 NEXT STEPS:")
        print("1. Check Stratz documentation for correct API usage")
        print("2. Verify your API keys are active and have the right permissions")
        print("3. Contact Stratz support about API access")
        print("4. Consider using OpenDota API as alternative")


if __name__ == "__main__":
    main()
