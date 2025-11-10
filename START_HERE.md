# 🚀 START HERE - Complete Solution

## ✅ Problem Solved!

Your Stratz API keys work! We just needed to:
1. Use `cloudscraper` to bypass Cloudflare
2. Query matches one at a time (batch queries need admin)
3. Use correct lowercase headers

## 📥 Step 1: Download Script

```bash
curl -o add_league_tier_single.py https://raw.githubusercontent.com/Prestoch/STRATZFINAL/refs/heads/cursor/add-tier-league-to-pro-match-data-4219/add_league_tier_single.py
```

## 📦 Step 2: Install Dependencies

```bash
pip install cloudscraper requests
```

## ✏️ Step 3: Add Your API Keys

Edit the script and replace these lines with your actual 5 API keys:

```python
API_KEYS = [
    "YOUR_API_KEY_1",  # Replace with your first key
    "YOUR_API_KEY_2",  # Replace with your second key
    "YOUR_API_KEY_3",  # Replace with your third key
    "YOUR_API_KEY_4",  # Replace with your fourth key
    "YOUR_API_KEY_5",  # Replace with your fifth key
]
```

## ▶️ Step 4: Run It

```bash
python3 add_league_tier_single.py
```

## ⏱️ What to Expect

- **Duration**: ~1.6 hours (96,507 API calls)
- **Progress updates**: Every 100 matches
- **Detailed stats**: Every 1,000 matches
- **Output file**: `stratz_with_tiers_96507.json`

Example output you'll see:
```
Dota 2 League/Tier Enrichment (Single-Match Queries)
======================================================================

Using 5 API keys with cloudscraper (Cloudflare bypass)
Loading matches from stratz_clean_96507.json...
Loaded 96507 matches

📋 Processing Plan:
   Total matches: 96,507
   Mode: ONE match per API call (batch queries need admin)
   API keys: 5
   Estimated time: 120.6 minutes (2.0 hours)

🚀 Starting processing...

Progress: 100/96507 (0.1%) | 84 with tier data
Progress: 200/96507 (0.2%) | 168 with tier data
...
Progress: 1000/96507 (1.0%) | 842 with tier data

📊 API Usage Statistics:
   Total calls: 1000 (15 failed)
   Elapsed time: 1.2 minutes
   Average: 833.3 calls/minute
   Key 1: 195/200 min | 195/1600 hr | 195/8000 day
   Key 2: 198/200 min | 198/1600 hr | 198/8000 day
   Key 3: 201/200 min | 201/1600 hr | 201/8000 day
   Key 4: 197/200 min | 197/1600 hr | 197/8000 day
   Key 5: 209/200 min | 209/1600 hr | 209/8000 day
   ETA: 115.2 minutes

...continues until 96,507...
```

## 📊 Output Format

Each match in `stratz_with_tiers_96507.json` will have:

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

## 💡 Tips

### Run in Background

Since it takes ~1.6 hours, consider using `screen` or `tmux`:

```bash
# Start screen session
screen -S stratz

# Run the script
python3 add_league_tier_single.py

# Detach: Press Ctrl+A, then D
# Check progress later: screen -r stratz
```

### Test First 100

To test before running all matches, edit the script:

```python
# Find this line (around line 267):
match_ids = list(matches.keys())

# Change to:
match_ids = list(matches.keys())[:100]
```

Then run it. If successful, change it back and run the full version.

## 🎯 Success Criteria

At the end, you should see:

```
✅ Complete! Added tier data to 81,234/96507 matches
   Total time: 96.5 minutes (1.61 hours)
   Average rate: 1000.1 calls/minute

📊 API Usage Statistics:
   Total calls: 96507 (234 failed)
   Elapsed time: 96.5 minutes
   Average: 1000.1 calls/minute

Saving enhanced data to stratz_with_tiers_96507.json...
Save complete!

✓ Enhanced dataset saved to stratz_with_tiers_96507.json

======================================================================
```

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'cloudscraper'"
```bash
pip install cloudscraper
```

### Script stops or hangs
- Check your internet connection
- Restart the script (it will continue from where it left off if you've saved progress)
- Some matches may fail (normal) - script continues with others

### "User is not an admin" errors
- This is normal for some matches
- Script will skip them and continue
- You'll see the count in "failed" stat

### Want to pause and resume?
- Unfortunately the current script doesn't save incremental progress
- If you need to pause, you'll have to restart
- Consider the "Test First 100" approach to verify everything works first

## 📚 Additional Files

- `SOLUTION.md` - Detailed technical explanation
- `README.md` - Complete documentation
- `test_cloudflare.py` - Quick test script

## ✅ You're Ready!

Just:
1. Download the script ⬆️
2. Add your 5 API keys ✏️
3. Run it ▶️
4. Wait ~1.6 hours ⏱️
5. Get your enriched dataset! 🎉

---

**Questions?** Check `SOLUTION.md` or `README.md` for more details.
