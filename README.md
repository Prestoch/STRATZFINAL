# Stratz League/Tier Data Fetcher - 403 Troubleshooting

Your API keys are returning **403 Forbidden** errors. This means we need to figure out how Stratz actually expects API calls to be made.

## 🔍 Quick Diagnosis Tools

### Option 1: Test Different API Methods (Python)
Try different authentication approaches to see what works:

```bash
python3 alternative_fetch_methods.py
```

This tests 7 different ways to call the Stratz API with your keys.

### Option 2: Use Browser Console (JavaScript)
The browser might have active session auth that works:

**Simple test:**
1. Go to https://stratz.com/
2. Press F12 > Console
3. Paste `stratz_console_simple.js` content
4. Run: `await testFetch()`

**Full fetcher:**
1. Go to https://stratz.com/
2. Press F12 > Console  
3. Paste `stratz_console_fetch.js` content
4. Follow the instructions in the console

### Option 3: Inspect Real API Calls
See exactly how Stratz's website calls their API:

**Follow instructions in:** `inspect_stratz_api.md`

Key steps:
1. Open https://stratz.com/matches/6449050893
2. Open DevTools (F12) > Network tab
3. Filter by "Fetch/XHR"
4. Look for requests to `api.stratz.com/graphql`
5. Right-click > Copy > Copy as cURL
6. Share the cURL command (mask your tokens)

## 📁 Files Overview

| File | Purpose |
|------|---------|
| `alternative_fetch_methods.py` | Tests 7 different API methods |
| `stratz_console_simple.js` | Simple browser console test |
| `stratz_console_fetch.js` | Full browser-based fetcher |
| `inspect_stratz_api.md` | Guide to inspect real API calls |
| `test_api.py` | Original API key test (currently failing with 403) |
| `add_league_tier.py` | Main script (needs working API method) |
| `add_league_tier_sample.py` | Sample script (needs working API method) |

## 🤔 Why 403 Forbidden?

Possible reasons:
1. **API keys are for a different endpoint** - Maybe there's a REST API instead of GraphQL
2. **Different auth header needed** - Maybe `X-Api-Key` instead of `Bearer`
3. **GraphQL query not allowed** - Maybe this query requires special permissions
4. **Need to be logged in** - Browser session auth instead of API keys
5. **API plan limitations** - Your plan might not include GraphQL access

## 🔄 Next Steps

### Step 1: Choose your approach

**A) Quick Test - Try Alternative Methods**
```bash
# Edit alternative_fetch_methods.py, add your API key
python3 alternative_fetch_methods.py
```

**B) Browser Console - Use Active Session**
1. Open https://stratz.com/ in Chrome
2. F12 > Console
3. Paste `stratz_console_simple.js`
4. Run: `await testFetch()`

**C) Inspect Real Calls - See What Works**
Follow `inspect_stratz_api.md` guide to capture actual working requests

### Step 2: Share Results

Once you find what works, share:
- The working URL/endpoint
- The headers that work
- The request format
- The response you get

Then I can update the main scripts to use the working method!

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
