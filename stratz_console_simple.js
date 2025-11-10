/**
 * Simplified Stratz Fetcher - Chrome Console
 * 
 * INSTRUCTIONS:
 * 1. Go to https://stratz.com/ (you don't need to be logged in)
 * 2. Open DevTools (F12) > Console tab
 * 3. Paste this script and press Enter
 * 4. Run: await fetchAllLeagueData()
 */

// Load your matches data first
async function loadMatchesFromFile() {
    // You'll need to paste your matches data here or load it
    // For now, return a placeholder
    console.log('Please paste your matches data into window.matchesData = {...}');
}

// Fetch league data for a batch of matches
async function fetchBatch(matchIds) {
    const query = `
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
    `;
    
    const response = await fetch('https://api.stratz.com/graphql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: query,
            variables: { matchIds: matchIds.map(id => parseInt(id)) }
        }),
        credentials: 'include'
    });
    
    const data = await response.json();
    console.log('Response:', response.status, data);
    return data;
}

// Test with a few match IDs
async function testFetch() {
    console.log('Testing with sample match IDs...');
    const result = await fetchBatch(['6449050893', '6449058478', '6449061020']);
    console.log('Result:', result);
}

console.log('✅ Script loaded! Run: await testFetch()');
