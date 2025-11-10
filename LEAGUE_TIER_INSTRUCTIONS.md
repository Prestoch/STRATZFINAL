# Adding League Tier Data to Dota 2 Matches

This guide explains how to add league and tier information to your Dota 2 pro matches dataset.

## Overview

Your current dataset (`stratz_clean_96507.json`) contains 96,507 pro matches with hero compositions but is missing league/tier information. The script `add_league_tier.py` will fetch this data from the Stratz API and create an enhanced dataset.

## Prerequisites

1. **Python 3.6+** with the `requests` library:
   ```bash
   pip install requests
   ```

2. **5 Stratz API keys** - You mentioned you have these available

## Setup Instructions

### Step 1: Add Your API Keys

Edit the `add_league_tier.py` file and replace the placeholder API keys with your actual keys:

```python
API_KEYS = [
    "YOUR_ACTUAL_API_KEY_1",
    "YOUR_ACTUAL_API_KEY_2",
    "YOUR_ACTUAL_API_KEY_3",
    "YOUR_ACTUAL_API_KEY_4",
    "YOUR_ACTUAL_API_KEY_5",
]
```

### Step 2: Run the Script

```bash
python3 add_league_tier.py
```

## What the Script Does

1. **Loads your existing dataset** (`stratz_clean_96507.json`)
2. **Processes matches in batches** of 50 to respect API rate limits
3. **Rotates through your 5 API keys** to maximize throughput
4. **Fetches league data** for each match using Stratz GraphQL API
5. **Adds three new fields** to each match:
   - `leagueId`: The ID of the league
   - `leagueName`: The display name of the league
   - `leagueTier`: The tier of the league (this is what you need!)
6. **Saves the enhanced dataset** as `stratz_with_tiers_96507.json`

## Output Format

After running, each match will have the league information added:

```json
{
  "8459753144": {
    "radiantWin": true,
    "radiantRoles": [...],
    "direRoles": [...],
    "leagueId": 12345,
    "leagueName": "The International 2023",
    "leagueTier": "PREMIUM"
  }
}
```

## League Tiers

Stratz typically uses these tier classifications:
- `PREMIUM` - Major tournaments (TI, Majors)
- `PROFESSIONAL` - Professional tournaments
- `AMATEUR` - Amateur/semi-pro tournaments
- `UNSET` or `null` - No tier assigned

## Performance

- Processing ~96,000 matches
- Batch size: 50 matches per API call
- Estimated time: 30-60 minutes (depending on API rate limits)
- The script includes progress indicators

## Troubleshooting

### Rate Limiting
If you hit rate limits, the script will:
- Automatically rotate to the next API key
- Wait and retry if all keys are rate-limited

### API Key Issues
If an API key is invalid:
- The script will skip it and rotate to the next one
- Check that your keys are valid Bearer tokens

### Adjusting Rate Limits
If needed, modify the `rate_limit_per_minute` in the script:
```python
self.rate_limit_per_minute = 100  # Adjust this value
```

## Next Steps

After the script completes:
1. Your original file remains unchanged
2. New enhanced file: `stratz_with_tiers_96507.json`
3. You can now filter/analyze matches by league tier!

## Questions?

The script includes detailed logging so you can monitor progress. If issues arise, check:
- API key validity
- Network connectivity
- Stratz API status
