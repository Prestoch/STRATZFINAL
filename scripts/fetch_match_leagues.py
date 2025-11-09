#!/usr/bin/env python3
"""Fetch league info for matches in stratz_clean_96507.json via STRATZ GraphQL (single-match).

Usage:
  python scripts/fetch_match_leagues.py --keys key1 key2 ... [--threads 5]

Writes match_leagues.json mapping matchId -> {"leagueId": int, "leagueName": str, "tier": int}.
Respects STRATZ rate limits by sleeping ~0.35s per key. Resumable.
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
DEFAULT_THREADS = 5
PER_KEY_DELAY = 0.35
REQUEST_TIMEOUT = 15
MAX_RETRIES = 5
GRAPHQL_ENDPOINT = 'https://api.stratz.com/graphql'

MATCH_QUERY = '''
query MatchLeague($id: Long!) {
  match(id: $id) {
    id
    league { id name tier }
  }
}
'''

BASE_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) STRATZFetcher/1.0',
    'Origin': 'https://stratz.com',
    'Referer': 'https://stratz.com/',
}


def fetch_match(match_id: int, token: str):
    headers = BASE_HEADERS.copy()
    headers["Authorization"] = f"Bearer {token}"
    payload = {'query': MATCH_QUERY, 'variables': {'id': match_id}}
    resp = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    if resp.status_code == 403:
        raise requests.HTTPError(
            f"403 Forbidden (token may lack access or headers rejected): {resp.text[:200]}",
            response=resp,
        )
    resp.raise_for_status()
    data = resp.json()
    match = data.get('data', {}).get('match')
    if not match:
        raise ValueError('match not found in response')
    league = match.get('league')
    if not league:
        return None
    return {
        'leagueId': league.get('id'),
        'leagueName': league.get('name'),
        'tier': league.get('tier'),
    }


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
                match_id = self.task_queue.get(timeout=3)
            except queue.Empty:
                return
            retry_count = 0
            while True:
                try:
                    token = self.key_queue.get(timeout=3)
                except queue.Empty:
                    time.sleep(0.5)
                    continue
                try:
                    time.sleep(PER_KEY_DELAY)
                    info = fetch_match(match_id, token)
                    with self.lock:
                        if info:
                            self.result_dict[str(match_id)] = info
                    break
                except Exception as exc:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        print(f"Match {match_id} failed after {MAX_RETRIES} retries: {exc}")
                        break
                    else:
                        print(f"Retry {retry_count} for match {match_id} due to: {exc}")
                        time.sleep(1.0 * retry_count)
                finally:
                    self.key_queue.put(token)
            self.task_queue.task_done()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keys', nargs='+', required=True, help='STRATZ API tokens (Bearer)')
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

    to_fetch = 0
    for mid in match_ids:
        if str(mid) in existing:
            continue
        task_q.put(int(mid))
        to_fetch += 1
    if to_fetch == 0:
        print("Nothing to fetch")
        return
    print(f"Queued {to_fetch} matches")

    result_dict = existing

    workers = [Worker(key_q, task_q, result_dict, lock) for _ in range(args.threads)]
    for w in workers:
        w.start()
    task_q.join()

    OUTPUT_FILE.write_text(json.dumps(result_dict, indent=2))
    print(f"Done. wrote {len(result_dict)} entries to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
