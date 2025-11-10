#!/usr/bin/env python3
"""
Script to fetch league/tier data for Dota 2 pro matches from Stratz API
and add it to the existing dataset.
"""

import json
import time
import requests
from typing import Dict, List, Optional
from collections import deque

# Stratz GraphQL endpoint
STRATZ_API_URL = "https://api.stratz.com/graphql"

# API keys (you'll need to provide these)
API_KEYS = [
    "YOUR_API_KEY_1",
    "YOUR_API_KEY_2",
    "YOUR_API_KEY_3",
    "YOUR_API_KEY_4",
    "YOUR_API_KEY_5",
]

class StratzAPIClient:
    def __init__(self, api_keys: List[str]):
        self.api_keys = deque(api_keys)
        self.current_key_index = 0
        self.request_count = 0
        self.rate_limit_per_minute = 100  # Adjust based on Stratz rate limits
        self.last_reset_time = time.time()
        
    def rotate_key(self):
        """Rotate to the next API key"""
        self.api_keys.rotate(-1)
        print(f"Rotated to API key {len(self.api_keys) - list(self.api_keys).index(self.api_keys[0])}")
        
    def get_current_key(self) -> str:
        """Get the current API key"""
        return self.api_keys[0]
    
    def check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        if current_time - self.last_reset_time >= 60:
            self.request_count = 0
            self.last_reset_time = current_time
        
        if self.request_count >= self.rate_limit_per_minute:
            sleep_time = 60 - (current_time - self.last_reset_time)
            if sleep_time > 0:
                print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_reset_time = time.time()
    
    def fetch_match_league_data(self, match_ids: List[str]) -> Dict:
        """
        Fetch league/tier data for a batch of match IDs
        
        Returns dict mapping match_id -> league data
        """
        self.check_rate_limit()
        
        # GraphQL query to get league information
        query = """
        query GetMatchLeagues($matchIds: [Long!]!) {
            matches(ids: $matchIds) {
                id
                leagueId
                league {
                    id
                    displayName
                    tier
                }
            }
        }
        """
        
        variables = {
            "matchIds": [int(mid) for mid in match_ids]
        }
        
        headers = {
            "Authorization": f"Bearer {self.get_current_key()}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                STRATZ_API_URL,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30
            )
            
            self.request_count += 1
            
            if response.status_code == 429:  # Rate limited
                print("Rate limited, rotating API key...")
                self.rotate_key()
                time.sleep(2)
                return self.fetch_match_league_data(match_ids)
            
            if response.status_code == 401:  # Unauthorized
                print("API key invalid, rotating...")
                self.rotate_key()
                return self.fetch_match_league_data(match_ids)
            
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                print(f"GraphQL errors: {data['errors']}")
                return {}
            
            # Parse response into dict
            result = {}
            if "data" in data and "matches" in data["data"]:
                for match in data["data"]["matches"]:
                    if match:
                        match_id = str(match["id"])
                        result[match_id] = {
                            "leagueId": match.get("leagueId"),
                            "leagueName": match.get("league", {}).get("displayName") if match.get("league") else None,
                            "leagueTier": match.get("league", {}).get("tier") if match.get("league") else None
                        }
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            time.sleep(5)
            return {}


def load_matches(filepath: str) -> Dict:
    """Load the matches JSON file"""
    print(f"Loading matches from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} matches")
    return data


def save_matches(filepath: str, data: Dict):
    """Save the enhanced matches JSON file"""
    print(f"Saving enhanced data to {filepath}...")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print("Save complete!")


def process_matches(matches: Dict, api_client: StratzAPIClient, batch_size: int = 50):
    """
    Process all matches and add league/tier data
    """
    match_ids = list(matches.keys())
    total_matches = len(match_ids)
    processed = 0
    added_data = 0
    
    print(f"\nProcessing {total_matches} matches in batches of {batch_size}...")
    
    for i in range(0, total_matches, batch_size):
        batch_ids = match_ids[i:i+batch_size]
        
        print(f"Processing batch {i//batch_size + 1}/{(total_matches + batch_size - 1)//batch_size} "
              f"(matches {i+1}-{min(i+batch_size, total_matches)})...")
        
        league_data = api_client.fetch_match_league_data(batch_ids)
        
        # Add league data to matches
        for match_id in batch_ids:
            if match_id in league_data:
                matches[match_id].update(league_data[match_id])
                if league_data[match_id].get("leagueTier") is not None:
                    added_data += 1
            else:
                # Add null values if no data found
                matches[match_id].update({
                    "leagueId": None,
                    "leagueName": None,
                    "leagueTier": None
                })
        
        processed += len(batch_ids)
        print(f"Progress: {processed}/{total_matches} ({100*processed/total_matches:.1f}%) - "
              f"{added_data} matches with tier data")
        
        # Small delay between batches
        time.sleep(0.5)
    
    print(f"\nComplete! Added tier data to {added_data}/{total_matches} matches")
    return matches


def main():
    """Main execution"""
    import sys
    
    # Check if API keys are provided
    if API_KEYS[0] == "YOUR_API_KEY_1":
        print("ERROR: Please add your Stratz API keys to the script!")
        print("Edit the API_KEYS list at the top of this file.")
        sys.exit(1)
    
    # Initialize API client
    api_client = StratzAPIClient(API_KEYS)
    
    # Load existing matches
    input_file = "stratz_clean_96507.json"
    matches = load_matches(input_file)
    
    # Process matches and add league data
    enhanced_matches = process_matches(matches, api_client)
    
    # Save enhanced dataset
    output_file = "stratz_with_tiers_96507.json"
    save_matches(output_file, enhanced_matches)
    
    print(f"\n✓ Enhanced dataset saved to {output_file}")
    print("The dataset now includes: leagueId, leagueName, and leagueTier for each match")


if __name__ == "__main__":
    main()
