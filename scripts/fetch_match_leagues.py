#!/usr/bin/env python3
"""Fetch league info (id, name, tier) for matches in stratz_clean_96507.json.

Usage:
  python scripts/fetch_match_leagues.py --keys key1 key2 ... [--batch-size 40] [--threads 5]

Respects STRATZ rate limits (~20 req/s; 250/min). This script enforces a conservative
per-key delay so we stay well below 200/minute, even with multiple threads.
It writes match_leagues.json mapping matchId -> {leagueId, leagueName, tier}.
Existing mapping is reused so the script is resumable.
"""
import argparse
import json
import queue
import threading
import time
from pathlib import Path

import requests

MATCHES_FILE = Path('stratz_clean_96507.json')
OUTPUT_FILE = Path('match_leagues.json')
GRAPHQL_ENDPOINT = 'https://api.stratz.com/graphql'
DEFAULT_BATCH_SIZE = 40
DEFAULT_THREADS = 5
PER_KEY_DELAY = 0.35  # seconds, ~3 calls per second => ~180 per minute per key
REQUEST_TIMEOUT = 15
MAX_RETRIES = 5

QUERY = '''
query MatchesLeagues($ids: [Long!]!) {
  matches(ids: $ids) {
    id
    league { id name tier }
  }
}
'''


class Worker(threading.Thread):
    def __init__(self, key_queue: queue.Queue, task_queue: queue.Queue, result_dict: dict, lock: threading.Lock):
        super().__init__(daemon=True)
        self.key_queue = key_queue
        self.task_queue = task_queue
        self.result_dict = result_dict
        self.lock = lock

    def run(self):
        while True:
            try:
                batch = self.task_queue.get(timeout=3)
            except queue.Empty:
                return
            retry_count = 0
            while True:
                try:
                    api_key = self.key_queue.get(timeout=3)
                except queue.Empty:
                    time.sleep(0.5)
                    continue
                try:
                    time.sleep(PER_KEY_DELAY)
                    headers = {"Authorization": f"Bearer {api_key}"}
                    resp = requests.post(
                        GRAPHQL_ENDPOINT,
                        json={'query': QUERY, 'variables': {'ids': batch}},
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    matches = data.get('data', {}).get('matches', [])
                    if not matches:
                        raise ValueError('No matches returned')
                    with self.lock:
                        for match in matches:
                            if not match:
                                continue
                            league = match.get('league')
                            if not league:
                                continue
                            self.result_dict[str(match['id'])] = {
                                'leagueId': league.get('id'),
                                'leagueName': league.get('name'),
                                'tier': league.get('tier'),
                            }
                    break
                except Exception as exc:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        print(f"Batch {batch[:3]} failed after {MAX_RETRIES} retries: {exc}")
                        break
                    else:
                        print(f"Retry {retry_count} for batch {batch[:3]} due to: {exc}")
                        time.sleep(1.0 * retry_count)
                finally:
                    self.key_queue.put(api_key)
            self.task_queue.task_done()


def chunked(iterable, size):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keys', nargs='+', required=True, help='STRATZ API keys (Bearer tokens)')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument('--threads', type=int, default=DEFAULT_THREADS)
    args = parser.parse_args()

    raw = json.loads(MATCHES_FILE.read_text())
    match_ids = list(raw.keys())
    print(f"Loaded {len(match_ids)} match ids")

    existing = {}
    if OUTPUT_FILE.exists():
        existing = json.loads(OUTPUT_FILE.read_text())
        print(f"Found existing mapping with {len(existing)} entries; will append new ones")

    task_q = queue.Queue()
    key_q = queue.Queue()
    lock = threading.Lock()

    for key in args.keys:
        key_q.put(key)

    new_batches = 0
    for batch in chunked(match_ids, args.batch_size):
        if all(str(mid) in existing for mid in batch):
            continue
        task_q.put([int(mid) for mid in batch])
        new_batches += 1
    if new_batches == 0:
        print("Nothing to fetch")
        return
    print(f"Queued {new_batches} batches (~{new_batches * args.batch_size} matches)")

    result_dict = existing

    workers = [Worker(key_q, task_q, result_dict, lock) for _ in range(args.threads)]
    for w in workers:
        w.start()
    task_q.join()

    OUTPUT_FILE.write_text(json.dumps(result_dict, indent=2))
    print(f"Done. wrote {len(result_dict)} entries to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
