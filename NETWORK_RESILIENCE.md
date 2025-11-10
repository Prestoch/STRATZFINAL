# Network Resilience & Resume Feature

## Problem: Long-Running Script Vulnerability

Original script issues:
- ❌ If network fails, matches are skipped
- ❌ If you stop the script, all progress is lost  
- ❌ If script crashes, you start from scratch
- ❌ Takes ~1.6 hours with no way to pause

## ✅ Solution: Checkpoint/Resume Script

New `add_league_tier_resume.py` features:

### 1. Automatic Checkpoints
- Saves progress **every 1,000 matches**
- Checkpoint file: `stratz_checkpoint.json`
- Includes: processed match IDs, current data, stats

### 2. Resume Capability
- If interrupted, run script again
- Automatically detects checkpoint
- Continues from where it left off
- No duplicate API calls

### 3. Network Error Handling
- **5 retries** per match (instead of 3)
- Exponential backoff (1s, 2s, 4s, 8s, 16s)
- Max wait: 30 seconds
- Tracks network errors separately

### 4. Graceful Interruption
- Press `Ctrl+C` to stop
- Saves checkpoint before exiting
- Can resume later

## How It Works

### First Run
```
🆕 Starting fresh (no checkpoint found)...

Processing Plan:
   Total matches: 96,507
   Already processed: 0
   Remaining: 96,507
   Checkpoint interval: Every 1,000 matches
   Estimated time: 120.6 minutes
```

### If Network Fails at Match 5,342
```
⚠️  Network error (attempt 1/5): Connection timeout
  Retrying in 1s...
⚠️  Network error (attempt 2/5): Connection timeout
  Retrying in 2s...
  ✓ Success on retry 3
```

### If You Stop Script (Ctrl+C) at Match 23,500
```
⚠️  Interrupted by user!
Saving checkpoint...
  💾 Checkpoint saved (23,500 matches)
✓ Progress saved. Run the script again to resume from here.
```

### Resume Later
```
✓ Found checkpoint: 23,500/96,507 matches processed

🔄 RESUMING from checkpoint...

Processing Plan:
   Total matches: 96,507
   Already processed: 23,500
   Remaining: 73,007
   Estimated time: 91.3 minutes
```

## Checkpoint File Structure

`stratz_checkpoint.json` contains:
```json
{
  "processed": 23500,
  "total": 96507,
  "processed_ids": ["6449050893", "6449058478", ...],
  "timestamp": 1731208563.45,
  "stats": {
    "total_calls": 23500,
    "failed_calls": 342,
    "network_errors": 15
  },
  "matches": {
    "6449050893": {
      "radiantWin": true,
      "leagueId": 15728,
      "leagueName": "The International 2023",
      "leagueTier": "PREMIUM",
      ...
    },
    ...
  }
}
```

## Usage

### Download
```bash
curl -o add_league_tier_resume.py https://raw.githubusercontent.com/Prestoch/STRATZFINAL/refs/heads/cursor/add-tier-league-to-pro-match-data-4219/add_league_tier_resume.py
```

### Add API Keys & Run
```bash
nano add_league_tier_resume.py  # Add your 5 API keys
python3 add_league_tier_resume.py
```

### If Interrupted
```bash
# Just run it again - it will resume automatically
python3 add_league_tier_resume.py
```

### Manual Checkpoint Control

To change checkpoint frequency, edit this line:
```python
CHECKPOINT_INTERVAL = 1000  # Change to 500, 2000, etc.
```

To manually delete checkpoint and start fresh:
```bash
rm stratz_checkpoint.json
```

## Network Failure Scenarios

### Scenario 1: Brief Network Hiccup
```
⚠️  Network error (attempt 1/5): Timeout
  Retrying in 1s...
  ✓ Success
```
**Result**: Match is fetched successfully after retry

### Scenario 2: Extended Outage
```
⚠️  Network error (attempt 1/5): Connection failed
  Retrying in 1s...
⚠️  Network error (attempt 2/5): Connection failed
  Retrying in 2s...
...
❌ Giving up on match 6449050893 after 5 attempts
```
**Result**: Match gets null values, script continues with next match

### Scenario 3: Complete Internet Loss
```
Progress: 15,200/96,507 (15.7%) | 12,845 with tier data
⚠️  Network error (attempt 1/5): No route to host
  Retrying in 1s...
⚠️  Network error (attempt 2/5): No route to host
  Retrying in 2s...
```
**Action**: Press `Ctrl+C` to save progress
**Result**: Checkpoint saved at 15,200 matches

## Comparison

| Feature | Original Script | Resume Script |
|---------|----------------|---------------|
| Checkpoint/Resume | ❌ No | ✅ Yes |
| Network retry | 3 attempts | 5 attempts |
| Graceful stop | ❌ No | ✅ Ctrl+C |
| Progress saved | ❌ Never | ✅ Every 1,000 |
| Resume after crash | ❌ No | ✅ Yes |
| Network error tracking | ❌ No | ✅ Yes |

## Recommendations

### For Stable Networks
- Use either script (both work fine)
- Resume script adds safety net

### For Unstable Networks
- **Definitely use resume script**
- Consider reducing checkpoint interval:
  ```python
  CHECKPOINT_INTERVAL = 500  # Save every 500 matches
  ```

### For Long Sessions
- **Use resume script**
- Run in `screen` or `tmux`
- Can disconnect and reconnect later

### Example with Screen
```bash
# Start screen session
screen -S stratz

# Run script
python3 add_league_tier_resume.py

# Detach: Ctrl+A, then D
# Your laptop can sleep/disconnect

# Reconnect later
screen -r stratz
# Script still running!
```

## Troubleshooting

### Checkpoint file corrupted
```bash
rm stratz_checkpoint.json
python3 add_league_tier_resume.py
# Starts fresh
```

### Want to start over
```bash
rm stratz_checkpoint.json
python3 add_league_tier_resume.py
```

### Check checkpoint status
```bash
# View checkpoint
cat stratz_checkpoint.json | jq '.processed, .total'
```

## Final Notes

- Checkpoint file can be large (~500MB+) as it contains all match data
- Final output removes checkpoint file automatically
- If script completes successfully, checkpoint is deleted
- Safe to run multiple times - won't duplicate work

---

**Recommendation**: Use `add_league_tier_resume.py` for production runs. The checkpoint feature makes the 1.6-hour process much safer!
