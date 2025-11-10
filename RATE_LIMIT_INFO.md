# Stratz API Rate Limit Implementation

## Rate Limits (Per API Key)

Stratz enforces these limits on each API key:

| Time Window | Limit per Key | With 5 Keys |
|-------------|---------------|-------------|
| Second      | 20 calls      | 100 calls   |
| Minute      | 250 calls     | 1,250 calls |
| Hour        | 2,000 calls   | 10,000 calls|
| Day         | 10,000 calls  | 50,000 calls|

## How the Scripts Handle Rate Limits

### Multi-Window Tracking

The `RateLimitTracker` class tracks API calls across **all four time windows** for each key:

```python
class RateLimitTracker:
    - Tracks calls in the last second
    - Tracks calls in the last minute
    - Tracks calls in the last hour
    - Tracks calls in the last day
```

Before making any API call, the tracker checks if **all four limits** are satisfied.

### Smart Key Rotation

Instead of simple round-robin rotation, the script intelligently selects keys:

1. **First choice**: Use the current key if it's available
2. **Second choice**: Find any other key that's available
3. **If all keys are rate-limited**: Calculate the minimum wait time and pause

This ensures maximum throughput while respecting all rate limits.

### Automatic Waiting

When all keys hit a rate limit, the script:
1. Calculates how long until the next key becomes available
2. Pauses for that duration (plus a small buffer)
3. Resumes processing automatically

Example output:
```
⏳ Rate limit reached on all keys. Waiting 2.3s...
```

## Performance Estimates

For your dataset (96,507 matches):

### API Calls Needed
- Batch size: 50 matches per call
- Total calls: 96,507 ÷ 50 = **1,931 API calls**

### Theoretical Maximum (5 keys)
- 1,250 calls/minute combined
- Time needed: 1,931 ÷ 1,250 = **~1.5 minutes**

### Conservative Estimate
- The script stays slightly under limits for safety
- Target rate: ~800 calls/minute
- Expected time: **2-3 minutes**

## Why This Approach is Better

### Before (Simple Rate Limiting)
- Only tracked calls per minute
- Fixed delay between batches
- Didn't account for second/hour/day limits
- Could still exceed limits during bursts

### After (Multi-Window Tracking)
- Tracks all four time windows
- No fixed delays (dynamically calculated)
- Prevents exceeding any limit
- Maximizes throughput within constraints

## Monitoring

The scripts provide detailed monitoring:

### Per-Batch Updates
```
Batch 1/1931 (matches 1-50)... ✓ (0.1% | 42 with tier data)
```

### Statistics Every 100 Batches
```
📊 API Usage Statistics:
   Total calls: 500 (2 failed)
   Elapsed time: 2.3 minutes
   Average: 217.4 calls/minute
   Key 1: 102/250 min | 102/2000 hr | 102/10000 day
   Key 2: 98/250 min | 98/2000 hr | 98/10000 day
   Key 3: 100/250 min | 100/2000 hr | 100/10000 day
   Key 4: 95/250 min | 95/2000 hr | 95/10000 day
   Key 5: 105/250 min | 105/2000 hr | 105/10000 day
   ETA: 6.2 minutes
```

## Error Handling

The scripts handle various scenarios:

### 429 Rate Limited (Unexpected)
If Stratz returns a 429 despite our tracking:
- Script rotates to a different key
- Logs the event
- Retries the request

### 401 Unauthorized
If a key is invalid:
- Script automatically tries the next key
- Continues processing
- Logs which key failed

### Network Errors
For transient network issues:
- Retries up to 3 times with exponential backoff
- Continues with remaining matches if retry fails

## Testing

### Quick Test (test_api.py)
- Tests all 5 keys with a few matches
- Shows which keys are valid
- Displays combined rate limit capacity
- Takes ~10 seconds

### Sample Test (add_league_tier_sample.py)
- Processes 100 matches
- Tests the full rate limiting logic
- Creates sample output file
- Takes ~10-20 seconds

### Full Processing (add_league_tier.py)
- Processes all 96,507 matches
- Full monitoring and statistics
- Creates complete enhanced dataset
- Takes ~2-3 minutes

## Configuration

All scripts use the same rate limit configuration:

```python
RATE_LIMITS = {
    'second': 20,    # Per key limit
    'minute': 250,   # Per key limit
    'hour': 2000,    # Per key limit
    'day': 10000     # Per key limit
}
```

These match Stratz's documented limits. If your API plan has different limits, simply update this dictionary at the top of any script.

## Key Advantages

1. ✅ **Never exceeds limits** - Tracks all four time windows
2. ✅ **Maximum throughput** - Uses all 5 keys efficiently
3. ✅ **No manual tuning** - Automatically adapts to load
4. ✅ **Detailed monitoring** - See exactly what's happening
5. ✅ **Graceful degradation** - Handles invalid keys automatically
6. ✅ **Transparent** - Clear logging of all wait times and limits

---

**Ready to use**: All scripts are configured with these rate limits and ready to run!
