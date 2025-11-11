#!/usr/bin/env python3
"""
Fetch hero matchup data from dota2protracker.com and emit a JSON matrix.

Requires cloudscraper (`pip install cloudscraper`) to bypass Cloudflare checks.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cloudscraper


BASE_URL = "https://dota2protracker.com/api"
OUTPUT_PATH = Path("protracker_matchups.json")
REQUEST_DELAY_SECONDS = 0.35


def build_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False}
    )


def fetch_heroes(scraper: cloudscraper.CloudScraper) -> list[dict]:
    response = scraper.get(f"{BASE_URL}/heroes/list")
    response.raise_for_status()
    return response.json()


def fetch_matchups(
    scraper: cloudscraper.CloudScraper, hero_id: int, hero_slug: str
) -> dict:
    response = scraper.get(
        f"{BASE_URL}/hero/{hero_id}/matchups",
        params={"minified": "true", "min_matches": 0},
        headers={
            "Referer": f"https://dota2protracker.com/hero/{hero_slug}",
            "Origin": "https://dota2protracker.com",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def build_matrix(heroes: list[dict], scraper: cloudscraper.CloudScraper) -> dict:
    matrix: dict[int, dict[int, dict[str, float]]] = {}

    for hero in heroes:
        hero_id = hero["hero_id"]
        hero_slug = hero["npc"]

        scraper.get(
            f"https://dota2protracker.com/hero/{hero_slug}",
            headers={"Referer": "https://dota2protracker.com"},
            timeout=10,
        )

        data = fetch_matchups(scraper, hero_id, hero_slug)
        fields = {name: idx for idx, name in enumerate(data["fields"])}

        for row in data["data"]:
            if row[fields["position"]] != "all":
                continue

            other_id = row[fields["other_hero_id"]]
            matches = row[fields["matches"]]
            wins = row[fields["wins"]]

            if matches == 0:
                win_rate = 0.0
                delta = 0.0
            else:
                win_rate = wins / matches
                delta = (win_rate - 0.5) * 100

            matrix.setdefault(hero_id, {})[other_id] = {
                "win_rate": win_rate,
                "delta": delta,
                "matches": matches,
            }

        time.sleep(REQUEST_DELAY_SECONDS)

    return matrix


def main() -> None:
    scraper = build_scraper()
    heroes = fetch_heroes(scraper)

    id_to_name = {hero["hero_id"]: hero["displayName"] for hero in heroes}
    matrix = build_matrix(heroes, scraper)

    payload = {
        "hero_map": id_to_name,
        "matrix": matrix,
        "generated_at": time.time(),
    }

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote matchup data for {len(matrix)} heroes to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
