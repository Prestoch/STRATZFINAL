# How to Find the Right Stratz Query

You're absolutely right - if Stratz shows pro matches to regular users, there MUST be a query that works!

## 🔍 Method: Inspect Stratz Website

### Step 1: Go to Stratz Pro Matches Page

Open one of these URLs:
- https://stratz.com/matches/pro
- https://stratz.com/leagues
- Or any page that shows pro match listings

### Step 2: Open DevTools Network Tab

1. Press `F12` (or right-click → Inspect)
2. Go to **Network** tab
3. Filter by **Fetch/XHR**
4. **Clear** the log (trash icon)

### Step 3: Trigger API Calls

- Scroll the page
- Change filters
- Click "Load More"
- Navigate to different sections

### Step 4: Find GraphQL Queries

Look for requests to `api.stratz.com/graphql`

Click on one and check:
- **Payload** tab → See the GraphQL query
- **Response** tab → See what data it returns

### Step 5: Copy the Working Query

Right-click on the request → **Copy as cURL**

Then share it here!

## 🎯 What We're Looking For

A query that:
1. ✅ Returns match IDs
2. ✅ Doesn't require admin access
3. ✅ Filters by date range / tier / pro matches
4. ✅ Can be paginated (skip/take)

## 📋 Example Queries That Might Work

Based on common patterns, it could be something like:

### Option A: League-Based Discovery
```graphql
query GetLeagueMatches($leagueId: Int!) {
    league(id: $leagueId) {
        matches {
            id
            didRadiantWin
            players { ... }
        }
    }
}
```

### Option B: Search with Filters
```graphql
query SearchProMatches($request: SearchType!) {
    search {
        matches(request: $request) {
            id
            league { ... }
        }
    }
}
```

### Option C: Pro Match Feed
```graphql
query GetProMatchFeed($take: Int!, $skip: Int!) {
    proMatches(take: $take, skip: $skip) {
        id
        league { ... }
    }
}
```

## 🔧 Quick Test Script

Run this to test different query approaches:

```bash
curl -o discover_stratz_queries.py https://raw.githubusercontent.com/Prestoch/STRATZFINAL/refs/heads/cursor/add-tier-league-to-pro-match-data-4219/discover_stratz_queries.py

# Add your API key
nano discover_stratz_queries.py

# Run it
python3 discover_stratz_queries.py
```

This tests 8 different query patterns to find what works.

## 💡 The Key Insight

You're right - the answer is on Stratz's website! We just need to:

1. See what query the website uses
2. Copy that exact query
3. Use it in our script

The website wouldn't work for regular users if admin access was required!

## 🚀 Next Steps

**Option A**: Run `discover_stratz_queries.py` to test common patterns

**Option B**: Inspect Stratz website and share the working query you find

**Option C**: Share any GraphQL query you see working in the Network tab

Once we find the right query, I'll update the fetch script to use it! 🎯
