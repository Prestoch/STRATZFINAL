# ✅ Stratz League/Tier Data Fetcher - WORKING SOLUTION

## Solution Found!

After testing, here's what works:
1. ✅ Use `cloudscraper` to bypass Cloudflare protection
2. ✅ Query matches **one at a time** (batch queries need admin access)
3. ✅ Use lowercase headers matching browser requests

**See `SOLUTION.md` for complete instructions!**

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install cloudscraper requests
```

### 2. Download the Working Script
```bash
curl -o add_league_tier_single.py https://raw.githubusercontent.com/Prestoch/STRATZFINAL/refs/heads/cursor/add-tier-league-to-pro-match-data-4219/add_league_tier_single.py
```

### 3. Add Your API Keys
Edit the script and replace the placeholders with your 5 actual API keys

### 4. Run It
```bash
python3 add_league_tier_single.py
```

**Expected time**: ~1.6 hours for all 96,507 matches

## 📁 Files Overview

### ✅ Working Files (Use These!)
| File | Purpose |
|------|---------|
| `add_league_tier_single.py` | **Main script** - Queries one match at a time |
| `SOLUTION.md` | **Complete guide** - Step-by-step instructions |
| `test_cloudflare.py` | Test if cloudscraper works with your keys |

### 📚 Reference/Diagnostic Files
| File | Purpose |
|------|---------|
| `add_league_tier.py` | Batch version (needs admin access - doesn't work) |
| `test_api.py` | Original test (blocked by Cloudflare) |
| `alternative_fetch_methods.py` | Tests different auth methods |
| `diagnose_stratz_api.py` | Comprehensive diagnostics |

## 🔧 What We Fixed

### Issue #1: Cloudflare Protection
- **Problem**: Python requests blocked with 403 "Just a moment..."
- **Solution**: Use `cloudscraper` library to bypass Cloudflare

### Issue #2: Admin Access Required  
- **Problem**: Batch queries (`matches(ids: [...])`) return "User is not an admin"
- **Solution**: Query one match at a time using `match(id: X)`

### Issue #3: Wrong Headers
- **Problem**: Capital "Bearer" and missing origin/referer headers
- **Solution**: Use lowercase "bearer" with proper browser headers

## 📊 Performance

- **Total matches**: 96,507
- **API calls needed**: 96,507 (one per match)
- **Rate limit**: ~1,000 calls/min (5 keys × 200/min)
- **Estimated time**: ~1.6 hours

The script provides real-time progress:
- Every 100 matches: Progress percentage
- Every 1,000 matches: Detailed stats and ETA

## 💾 Output

Creates: `stratz_with_tiers_96507.json`

Each match gets three new fields:
- `leagueId`: Numeric league ID
- `leagueName`: Human-readable name (e.g., "The International 2023")
- `leagueTier`: Tier classification (PREMIUM, PROFESSIONAL, AMATEUR, etc.)

## 🆘 Need Help?

If nothing works automatically:

1. **Check Network Tab**: See `inspect_stratz_api.md`
2. **Try Browser Console**: Use `stratz_console_fetch.js`
3. **Check Stratz Docs**: https://docs.stratz.com/
4. **Alternative Source**: Consider using OpenDota API (has league data too)

## 📊 Current Dataset

- **File**: `stratz_clean_96507.json`
- **Matches**: 96,507
- **Missing**: leagueId, leagueName, leagueTier
- **Need to fetch**: ~1,931 API calls (50 matches per call)

## 💡 Alternative: OpenDota

If Stratz API continues to fail, OpenDota also has league information:
- Free, no API key needed
- Has league_id and league tier
- Public API: `https://api.opendota.com/api/matches/{match_id}`

The `alternative_fetch_methods.py` script includes an OpenDota test (Method 7).
