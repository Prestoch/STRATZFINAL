# Dota 2 Match League/Tier Data Enrichment

This project adds league and tier information to your Dota 2 pro matches dataset using the Stratz API.

## 📋 What You Have

- **Input**: `stratz_clean_96507.json` - 96,507 pro matches with hero compositions
- **Missing**: League names and tier classifications for each match
- **Resources**: 5 Stratz API keys

## 🔒 Stratz API Rate Limits (Per Key)

- **20 calls/second**
- **250 calls/minute**
- **2,000 calls/hour**
- **10,000 calls/day**

With 5 keys, your combined capacity:
- 100 calls/second
- 1,250 calls/minute
- 10,000 calls/hour
- 50,000 calls/day

## 🎯 What You'll Get

Enhanced dataset with three new fields for each match:
- `leagueId` - Numeric league identifier
- `leagueName` - Human-readable league name (e.g., "The International 2023")
- `leagueTier` - Tournament tier (PREMIUM, PROFESSIONAL, AMATEUR, etc.)

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Add Your API Keys

Edit **all three scripts** and add your 5 Stratz API keys:
- `test_api.py` - To test your keys
- `add_league_tier_sample.py` - To test with 100 matches
- `add_league_tier.py` - For full processing

Replace this section in each file:
```python
API_KEYS = [
    "YOUR_API_KEY_1",    # Replace with actual key
    "YOUR_API_KEY_2",    # Replace with actual key
    "YOUR_API_KEY_3",    # Replace with actual key
    "YOUR_API_KEY_4",    # Replace with actual key
    "YOUR_API_KEY_5",    # Replace with actual key
]
```

### Step 3: Test Your API Keys (Recommended)

```bash
python3 test_api.py
```

This will verify all 5 API keys work correctly without processing any data.

### Step 4: Run Sample Test (Recommended)

```bash
python3 add_league_tier_sample.py
```

This processes only 100 matches to verify everything works. Output: `stratz_sample_with_tiers.json`

### Step 5: Process All Matches

```bash
python3 add_league_tier.py
```

This processes all 96,507 matches. Output: `stratz_with_tiers_96507.json`

⏱️ **Estimated time**: ~2-3 minutes with 5 API keys (respecting rate limits)

## 📁 Files Included

| File | Purpose |
|------|---------|
| `test_api.py` | Test your API keys without processing data |
| `add_league_tier_sample.py` | Process 100 matches as a test |
| `add_league_tier.py` | Process all 96,507 matches |
| `requirements.txt` | Python dependencies |
| `LEAGUE_TIER_INSTRUCTIONS.md` | Detailed documentation |

## 📊 Expected Output Format

**Before:**
```json
{
  "8459753144": {
    "radiantWin": true,
    "radiantRoles": [...],
    "direRoles": [...]
  }
}
```

**After:**
```json
{
  "8459753144": {
    "radiantWin": true,
    "radiantRoles": [...],
    "direRoles": [...],
    "leagueId": 15728,
    "leagueName": "The International 2023",
    "leagueTier": "PREMIUM"
  }
}
```

## 🎮 League Tier Values

- `PREMIUM` - Major tournaments (The International, Majors)
- `PROFESSIONAL` - Professional tier tournaments  
- `AMATEUR` - Amateur/semi-professional tournaments
- `null` - No tier information available

## ⚙️ Features

✅ **Multi-Window Rate Limiting** - Tracks second/minute/hour/day limits per key
✅ **Smart API Key Rotation** - Automatically uses available keys
✅ **Batch Processing** - Processes 50 matches per API call for efficiency
✅ **Error Handling** - Retries on failures, handles invalid keys
✅ **Progress Tracking** - Real-time progress updates and ETA
✅ **Safe** - Original file is never modified
✅ **Efficient** - Stays just under rate limits for maximum throughput

## 🔧 Customization

### Adjust Batch Size
In any script, modify:
```python
batch_size = 50  # Change to 25, 100, etc.
```

### Adjust Rate Limits (if needed)
At the top of any script:
```python
RATE_LIMITS = {
    'second': 20,   # Calls per second per key
    'minute': 250,  # Calls per minute per key
    'hour': 2000,   # Calls per hour per key
    'day': 10000    # Calls per day per key
}
```

### Process Different Sample Size
In `add_league_tier_sample.py`:
```python
SAMPLE_SIZE = 100  # Change to 50, 500, etc.
```

## ❓ Troubleshooting

### "401 Unauthorized"
- Check that your API keys are valid
- Ensure you're using Bearer tokens, not other auth types

### "429 Rate Limited"
- The script will automatically rotate keys
- If all keys are limited, it will wait before retrying
- Consider reducing `rate_limit_per_minute`

### Some Matches Have null Tier
- This is normal - not all matches have league information
- Matches without leagues will have `null` values

### Script is Slow
- Normal processing time: 2-3 minutes for 96k matches with 5 keys
- Script includes automatic rate limiting to stay under Stratz limits
- Progress updates every 100 batches show ETA and throughput

## 📈 Progress Indicators

The script shows:
```
Processing batch 1/1931 (matches 1-50)...
Progress: 50/96507 (0.1%) - 42 matches with tier data
```

- **Batch number**: Current batch being processed
- **Progress percentage**: Overall completion
- **Matches with tier data**: How many have valid league info

## ✅ Success Criteria

After running the full script, you should see:
- New file created: `stratz_with_tiers_96507.json`
- Original file unchanged: `stratz_clean_96507.json`
- Each match now has `leagueId`, `leagueName`, and `leagueTier` fields
- Most matches have tier data (some may be `null`)

## 📚 Additional Resources

- [Stratz API Documentation](https://docs.stratz.com/)
- [Stratz GraphQL Playground](https://api.stratz.com/graphql)
- See `LEAGUE_TIER_INSTRUCTIONS.md` for more details

## 🐛 Need Help?

1. Run `test_api.py` first to isolate API issues
2. Try `add_league_tier_sample.py` to test with small dataset
3. Check the console output for specific error messages
4. Verify your API keys are active on Stratz

---

**Ready to start?** Follow the Quick Start guide above!
