/**
 * Stratz Match League/Tier Data Fetcher - Chrome Console Version
 * 
 * Instructions:
 * 1. Go to https://stratz.com/ and log in
 * 2. Open Chrome DevTools (F12)
 * 3. Go to Console tab
 * 4. Paste this entire script and press Enter
 * 5. The script will fetch league data for all matches and download a JSON file
 * 
 * This uses your browser's authenticated session, so no API key issues!
 */

(async function() {
    console.log('🚀 Stratz Match League/Tier Fetcher Starting...');
    console.log('═══════════════════════════════════════════════');
    
    // Configuration
    const BATCH_SIZE = 50; // Matches per request
    const DELAY_BETWEEN_BATCHES = 200; // ms delay to avoid rate limits
    
    // Load the matches data
    console.log('📂 Please provide the matches data...');
    console.log('');
    console.log('Copy and paste your stratz_clean_96507.json content, then run:');
    console.log('window.MATCHES_DATA = <paste your JSON here>;');
    console.log('');
    console.log('Then run: startFetching()');
    console.log('');
    
    // GraphQL endpoint
    const GRAPHQL_URL = 'https://api.stratz.com/graphql';
    
    // Function to fetch match league data
    async function fetchMatchLeagueData(matchIds) {
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
        
        const variables = {
            matchIds: matchIds.map(id => parseInt(id))
        };
        
        try {
            const response = await fetch(GRAPHQL_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query, variables }),
                credentials: 'include' // Use browser cookies for auth
            });
            
            if (!response.ok) {
                console.error(`❌ HTTP ${response.status}: ${response.statusText}`);
                return {};
            }
            
            const data = await response.json();
            
            if (data.errors) {
                console.error('❌ GraphQL errors:', data.errors);
                return {};
            }
            
            // Parse response
            const result = {};
            if (data.data && data.data.matches) {
                for (const match of data.data.matches) {
                    if (match) {
                        result[match.id.toString()] = {
                            leagueId: match.leagueId,
                            leagueName: match.league?.displayName || null,
                            leagueTier: match.league?.tier || null
                        };
                    }
                }
            }
            
            return result;
        } catch (error) {
            console.error('❌ Request error:', error);
            return {};
        }
    }
    
    // Function to process all matches
    async function processMatches(matches) {
        const matchIds = Object.keys(matches);
        const totalMatches = matchIds.length;
        const totalBatches = Math.ceil(totalMatches / BATCH_SIZE);
        
        console.log(`\n📋 Processing Plan:`);
        console.log(`   Total matches: ${totalMatches.toLocaleString()}`);
        console.log(`   Batch size: ${BATCH_SIZE}`);
        console.log(`   Total batches: ${totalBatches.toLocaleString()}`);
        console.log(`   Estimated time: ${(totalBatches * DELAY_BETWEEN_BATCHES / 1000 / 60).toFixed(1)} minutes`);
        console.log('');
        
        let processed = 0;
        let withTierData = 0;
        const startTime = Date.now();
        
        for (let i = 0; i < totalMatches; i += BATCH_SIZE) {
            const batchIds = matchIds.slice(i, i + BATCH_SIZE);
            const batchNum = Math.floor(i / BATCH_SIZE) + 1;
            
            console.log(`Batch ${batchNum}/${totalBatches} (${i+1}-${Math.min(i+BATCH_SIZE, totalMatches)})...`);
            
            const leagueData = await fetchMatchLeagueData(batchIds);
            
            // Add league data to matches
            for (const matchId of batchIds) {
                if (leagueData[matchId]) {
                    matches[matchId] = {
                        ...matches[matchId],
                        ...leagueData[matchId]
                    };
                    if (leagueData[matchId].leagueTier) {
                        withTierData++;
                    }
                } else {
                    matches[matchId] = {
                        ...matches[matchId],
                        leagueId: null,
                        leagueName: null,
                        leagueTier: null
                    };
                }
            }
            
            processed += batchIds.length;
            const percent = (processed / totalMatches * 100).toFixed(1);
            console.log(`  ✓ ${percent}% complete | ${withTierData} with tier data`);
            
            // Progress update every 100 batches
            if (batchNum % 100 === 0) {
                const elapsed = (Date.now() - startTime) / 1000 / 60;
                const rate = batchNum / elapsed;
                const remaining = (totalBatches - batchNum) / rate;
                console.log(`  📊 ${elapsed.toFixed(1)} min elapsed | ETA: ${remaining.toFixed(1)} min`);
            }
            
            // Delay between batches
            if (i + BATCH_SIZE < totalMatches) {
                await new Promise(resolve => setTimeout(resolve, DELAY_BETWEEN_BATCHES));
            }
        }
        
        const totalTime = (Date.now() - startTime) / 1000 / 60;
        console.log('');
        console.log('✅ Processing Complete!');
        console.log(`   Total time: ${totalTime.toFixed(1)} minutes`);
        console.log(`   Matches with tier data: ${withTierData}/${totalMatches}`);
        
        return matches;
    }
    
    // Function to download results
    function downloadResults(data, filename) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        console.log(`📥 Downloaded: ${filename}`);
    }
    
    // Make functions globally available
    window.startFetching = async function() {
        if (!window.MATCHES_DATA) {
            console.error('❌ Error: window.MATCHES_DATA not set!');
            console.log('Please set window.MATCHES_DATA first by pasting your JSON data.');
            return;
        }
        
        console.log('🚀 Starting to fetch league data...');
        const enhanced = await processMatches(window.MATCHES_DATA);
        
        console.log('');
        console.log('💾 Preparing download...');
        downloadResults(enhanced, 'stratz_with_tiers_96507.json');
        
        console.log('');
        console.log('═══════════════════════════════════════════════');
        console.log('✨ All done! Check your downloads folder.');
    };
    
    // Test function to check if auth is working
    window.testStratzAuth = async function() {
        console.log('🔍 Testing Stratz authentication...');
        
        const testQuery = `
            query {
                constants {
                    heroes {
                        id
                        displayName
                    }
                }
            }
        `;
        
        try {
            const response = await fetch(GRAPHQL_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: testQuery }),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (response.ok && data.data) {
                console.log('✅ Authentication working! You can use startFetching()');
                return true;
            } else {
                console.error('❌ Authentication failed:', data);
                return false;
            }
        } catch (error) {
            console.error('❌ Test failed:', error);
            return false;
        }
    };
    
    console.log('✅ Script loaded successfully!');
    console.log('');
    console.log('📝 Next steps:');
    console.log('1. Test auth: testStratzAuth()');
    console.log('2. Load data: window.MATCHES_DATA = <paste your JSON>');
    console.log('3. Start: startFetching()');
    console.log('');
    
})();
