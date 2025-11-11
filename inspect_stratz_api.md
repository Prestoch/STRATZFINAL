# How to Inspect Stratz API Calls

The 403 Forbidden errors suggest we need to see how Stratz actually makes API calls. Here's how to capture the real requests:

## Method 1: Chrome DevTools Network Tab

### Step 1: Open Stratz Website
1. Go to https://stratz.com/
2. Navigate to a match page (e.g., https://stratz.com/matches/6449050893)

### Step 2: Open DevTools
1. Press `F12` or right-click > Inspect
2. Go to the **Network** tab
3. Filter by **Fetch/XHR**
4. Clear the log (trash icon)

### Step 3: Trigger API Call
1. Refresh the match page or navigate to another match
2. Look for requests to `api.stratz.com/graphql`
3. Click on one of these requests

### Step 4: Copy Request Details
In the request details, check:
- **Headers** tab:
  - Look for `Authorization` header
  - Look for any custom headers
  - Copy the full request headers
- **Payload** tab:
  - Copy the GraphQL query they use
  - Copy the variables

### Step 5: Share What You Find
Look for patterns like:
- `Authorization: Bearer <token>`
- Any `X-Api-Key` headers
- Cookie-based authentication
- Different API endpoint URLs

## Method 2: Copy as cURL

1. In Network tab, find a GraphQL request
2. Right-click on it
3. Select **Copy** > **Copy as cURL**
4. Paste it and share the command

This will show exactly how their browser makes authenticated requests.

## Method 3: Use Chrome Console Script

### Step 1: Go to Stratz
Open https://stratz.com/ in Chrome

### Step 2: Open Console
Press `F12` > Console tab

### Step 3: Test Simple Request
Paste this and press Enter:

```javascript
fetch('https://api.stratz.com/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: `query { constants { heroes { id displayName } } }`
    }),
    credentials: 'include'
})
.then(r => r.json())
.then(d => console.log('Success:', d))
.catch(e => console.error('Error:', e));
```

### Step 4: Test Match Query
If that works, try:

```javascript
fetch('https://api.stratz.com/graphql', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        query: `query GetMatch($id: Long!) {
            match(id: $id) {
                id
                leagueId
                league {
                    displayName
                    tier
                }
            }
        }`,
        variables: { id: 6449050893 }
    }),
    credentials: 'include'
})
.then(r => r.json())
.then(d => console.log('Match data:', d))
.catch(e => console.error('Error:', e));
```

## Alternative: Check if REST API Exists

Try these URLs in your browser (while logged into Stratz):
- `https://api.stratz.com/api/v1/match/6449050893`
- `https://api.stratz.com/Match/6449050893`
- `https://api.stratz.com/api/match/6449050893`

## What We're Looking For

1. **Does Stratz use API keys at all for browser requests?**
   - Maybe they only use session cookies
   
2. **Is there a different API endpoint?**
   - Maybe GraphQL isn't the right endpoint
   
3. **Are there required headers?**
   - Some APIs need special headers like `X-Api-Key`

4. **Do the API keys work for a different endpoint?**
   - Maybe there's a REST API instead of GraphQL

## Once You Find the Real Request

Share:
1. The full URL
2. All headers (you can mask sensitive data)
3. The request body format
4. The response format

Then we can update the Python scripts to match exactly how Stratz expects requests!
