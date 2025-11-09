#!/usr/bin/env python3
"""Fetch league info (id, name, tier) for each match in stratz_clean_96507.json.

Usage:
  python scripts/fetch_match_leagues.py --keys key1 key2 ...

Writes match_leagues.json mapping matchId -> {"leagueId": int, "leagueName": str, "tier": int}.
Skips matches with missing league data. Safe to run incrementally; reuses existing output.
"""
import argparse
import json
import queue
import threading
from pathlib import Path

import requests

MATCHES_FILE = Path('stratz_clean_96507.json')
OUTPUT_FILE = Path('match_leagues.json')
DEFAULT_BATCH_SIZE = 50
GRAPHQL_ENDPOINT = 'https://api.stratz.com/graphql'

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
            try:
                api_key = self.key_queue.get(timeout=3)
            except queue.Empty:
                self.task_queue.put(batch)
                return
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = requests.post(
                    GRAPHQL_ENDPOINT,
                    json={'query': QUERY, 'variables': {'ids': batch}},
                    headers=headers,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                matches = data.get('data', {}).get('matches', [])
                if not matches:
                    print(f"No data returned for batch starting {batch[0]}")
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
            except Exception as exc:
                print(f"Error processing batch {batch[:3]}...: {exc}")
                self.task_queue.put(batch)
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
    parser.add_argument('--threads', type=int, default=10)
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

    for batch in chunked(match_ids, args.batch_size):
        if all(str(mid) in existing for mid in batch):
            continue
        task_q.put([int(mid) for mid in batch])

    if task_q.empty():
        print("Nothing to fetch")
        return

    result_dict = existing

    workers = [Worker(key_q, task_q, result_dict, lock) for _ in range(args.threads)]
    for w in workers:
        w.start()
    task_q.join()

    OUTPUT_FILE.write_text(json.dumps(result_dict, indent=2))
    print(f"Done. wrote {len(result_dict)} entries to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
