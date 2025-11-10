# Fetch Recent Pro Matches from Stratz

This guide is for **fetching NEW pro matches** from the last 6 months, not enriching existing data.

## What This Does

Queries Stratz API and fetches:
- ✅ All pro matches from last 6 months
- ✅ Hero picks for each team
- ✅ Player roles (carry, mid, offlane, support)
- ✅ League name and tier
- ✅ Match result (radiant win/loss)

## Output Format

Same format as your existing `stratz_clean_96507.json`:

```json
{
  "7234567890": {
    "radiantWin": true,
    "radiantRoles": [
      {"heroId": 77, "role": "carry"},
      {"heroId": 89, "role": "hardsupport"},
      {"heroId": 82, "role": "mid"},
      {"heroId": 28, "role": "offlane"},
      {"heroId": 123, "role": "softsupport"}
    ],
    "direRoles": [
      {"heroId": 71, "role": "mid"},
      {"heroId": 44, "role": "carry"},
      ...
    ],
    "leagueId": 15728,
    "leagueName": "The International 2023",
    "leagueTier": "PREMIUM"
  }
}
```

## Quick Start

### 1. Download
```bash
curl -o fetch_recent_pro_matches.py https://raw.githubusercontent.com/Prestoch/STRATZFINAL/refs/heads/cursor/add-tier-league-to-pro-match-data-4219/fetch_recent_pro_matches.py
```

### 2. Install Dependencies
```bash
pip install cloudscraper requests
```

### 3. Add Your API Keys
```bash
nano fetch_recent_pro_matches.py
# Replace YOUR_API_KEY_1 through YOUR_API_KEY_5
```

### 4. Run
```bash
python3 fetch_recent_pro_matches.py
```

## What to Expect

### Step 1: Discover Match IDs
```
🔍 Step 1: Discovering pro match IDs...
   Fetching PROFESSIONAL matches...
     Found 100 matches (total: 100)
     Found 100 matches (total: 200)
     ...
   Fetching PREMIUM matches...
     Found 85 matches (total: 1,285)
   ...

✓ Discovered 3,542 unique pro matches
```

### Step 2: Fetch Details
```
📥 Step 2: Fetching match details...
   Progress: 100/3542 (2.8%) | 98 successful
   Progress: 200/3542 (5.6%) | 195 successful
   ...
   Progress: 3500/3542 (98.8%) | 3,421 successful

✅ Fetched details for 3,421/3,542 matches
```

### Output
```
💾 Saving to stratz_pro_matches_6months_20231110.json...
✓ Saved 3,421 matches

📊 Statistics:
   Total API calls: 3,638
   Failed calls: 217
   Time elapsed: 4.2 minutes
   Average rate: 866.2 calls/min

✓ Done! Output: stratz_pro_matches_6months_20231110.json
```

## Customization

### Change Time Range

Edit these lines in the script:

```python
# For 3 months instead of 6
START_TIME = int((datetime.now() - timedelta(days=90)).timestamp())

# For 1 year
START_TIME = int((datetime.now() - timedelta(days=365)).timestamp())

# For specific date range
START_TIME = int(datetime(2023, 6, 1).timestamp())
END_TIME = int(datetime(2023, 12, 1).timestamp())
```

### Change Pro Tiers

Edit the `PRO_TIERS` list:

```python
# Only highest tier tournaments
PRO_TIERS = ["PREMIUM", "INTERNATIONAL"]

# Include more tiers
PRO_TIERS = ["PROFESSIONAL", "PREMIUM", "DPC_QUALIFIER", "DPC_LEAGUE", 
             "DPC_LEAGUE_FINALS", "MAJOR", "MINOR", "INTERNATIONAL"]
```

### Available Tiers

- `PREMIUM` - Major tournaments (TI, Majors)
- `PROFESSIONAL` - Professional tournaments
- `INTERNATIONAL` - International competitions
- `DPC_QUALIFIER` - DPC Qualifiers
- `DPC_LEAGUE` - DPC Regional Leagues
- `DPC_LEAGUE_QUALIFIER` - DPC League Qualifiers
- `DPC_LEAGUE_FINALS` - DPC League Finals
- `MAJOR` - Major tournaments
- `MINOR` - Minor tournaments

## Performance

### Expected Numbers (Last 6 Months)

- **Matches**: ~2,000-5,000 (depends on tournament schedule)
- **API calls**: ~3,000-8,000
- **Time**: 3-10 minutes
- **Rate**: ~800-1,000 calls/minute with 5 keys

### Slower Than Expected?

The script makes 2 types of calls:
1. **Discovery**: Get match IDs from leagues (~10-50 calls)
2. **Details**: Get full match data (~1 call per match)

Most time is spent in Step 2 (fetching details).

## Comparison: Two Different Tasks

### Task 1: Enrich Existing Dataset
**Use**: `add_league_tier_resume.py`
- You already have match IDs
- Just adding tier/league data
- ~96,507 API calls
- ~1.6 hours

### Task 2: Fetch New Matches (This Script)
**Use**: `fetch_recent_pro_matches.py`
- Discovering new match IDs
- Fetching full match details
- ~3,000-8,000 API calls
- ~3-10 minutes

## Combining Both

If you want to:
1. Fetch recent 6-month matches (with roles + tier)
2. Then enrich your old dataset with tier data

Run both scripts:

```bash
# First: Get recent matches
python3 fetch_recent_pro_matches.py
# Output: stratz_pro_matches_6months_20231110.json

# Second: Enrich old dataset
python3 add_league_tier_resume.py
# Output: stratz_with_tiers_96507.json

# Optional: Merge both datasets
python3 -c "
import json
old = json.load(open('stratz_with_tiers_96507.json'))
new = json.load(open('stratz_pro_matches_6months_20231110.json'))
old.update(new)
json.dump(old, open('stratz_complete_dataset.json', 'w'), indent=2)
print(f'Merged: {len(old)} total matches')
"
```

## Troubleshooting

### "No matches found"
- Check time range (maybe no pro tournaments in that period)
- Verify tier names are correct
- Some tiers might be empty

### "Admin error"
- This script queries leagues, not batch matches
- Should work without admin access
- If it fails, the tier might require admin

### Getting old matches
- Change `START_TIME` to go further back
- Note: Very old matches might have missing data

### Want to filter by region?
The script currently gets all regions. To filter, you'd need to add region filtering to the league query.

## Output Files

- **Main output**: `stratz_pro_matches_6months_YYYYMMDD.json`
- **Format**: Same as your existing dataset
- **Can be merged**: With existing datasets

## Next Steps

After fetching:
1. Verify data quality
2. Check for missing fields
3. Merge with existing datasets if needed
4. Use for analysis!

---

**This script fetches NEW matches. Use `add_league_tier_resume.py` to enrich EXISTING matches.**
