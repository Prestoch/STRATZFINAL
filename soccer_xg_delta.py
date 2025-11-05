#!/usr/bin/env python3
"""Soccer xG delta analysis leveraging StatsBomb open-data.

This script mirrors the functionality of `nba_delta.pl` but adapts it for
football (soccer) by mapping formations/positions into tactical roles and
computing per-role expected-goals (xG) edges. It supports two primary modes:

1. `backtest` (default): ingest a large corpus of historical matches (10K+),
   derive role-based offensive and defensive strengths, trigger 1X2 wagers when
   the combined xG swing crosses a configurable threshold, and export the
   accuracy results to CSV.
2. `single`: compute the current-role deltas between two specific clubs using
   accumulated historical data.

The script consumes StatsBomb's public open-data repository directly from
GitHub and caches the payloads locally to avoid redundant downloads.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests


STATS_BOMB_BASE = (
    "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
)

ROLES = ["striker", "wide_forward", "midfield_pivot", "fullback", "center_back"]

DEFENSE_TARGET_MAP = {
    "striker": "center_back",
    "wide_forward": "fullback",
    "midfield_pivot": "midfield_pivot",
    "fullback": "fullback",
    "center_back": "center_back",
    "goalkeeper": "center_back",
    "other": "midfield_pivot",
}

DEFAULT_THRESHOLD = 0.4
DEFAULT_MIN_MATCHES = 5


@dataclass
class RoleSplit:
    total: float = 0.0
    matches: int = 0

    def add(self, value: float) -> None:
        self.total += value

    def bump_matches(self) -> None:
        self.matches += 1

    def average(self) -> float:
        return self.total / self.matches if self.matches else 0.0


class StatsBombClient:
    """Thin client around StatsBomb open-data with on-disk caching."""

    def __init__(
        self,
        cache_dir: Path,
        retries: int = 3,
        backoff: float = 0.5,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.retries = retries
        self.backoff = backoff

    def fetch_json(self, category: str, filename: str) -> Any:
        category_dir = self.cache_dir / category if category else self.cache_dir
        category_dir.mkdir(parents=True, exist_ok=True)
        cache_path = category_dir / filename
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            with cache_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)

        url_parts = [STATS_BOMB_BASE.rstrip("/")]
        if category:
            url_parts.append(category.strip("/"))
        url_parts.append(filename.lstrip("/"))
        url = "/".join(url_parts)
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, timeout=60)
                if response.status_code == 200:
                    payload = response.json()
                    with cache_path.open("w", encoding="utf-8") as handle:
                        json.dump(payload, handle)
                    return payload
                logging.warning(
                    "Failed to fetch %s (status %s, attempt %s/%s)",
                    url,
                    response.status_code,
                    attempt,
                    self.retries,
                )
            except requests.RequestException as exc:  # pragma: no cover - network
                logging.warning(
                    "Error fetching %s on attempt %s/%s: %s",
                    url,
                    attempt,
                    self.retries,
                    exc,
                )
            time.sleep(self.backoff * attempt)

        raise RuntimeError(f"Unable to fetch {url} after {self.retries} attempts")

    def competitions(self) -> List[Dict[str, Any]]:
        data = self.fetch_json("", "competitions.json")
        return sorted(
            data,
            key=lambda comp: (
                comp.get("season_name", ""),
                comp.get("competition_name", ""),
            ),
        )

    def matches(self, competition_id: int, season_id: int) -> List[Dict[str, Any]]:
        filename = f"{competition_id}/{season_id}.json"
        return self.fetch_json("matches", filename)

    def lineups(self, match_id: int) -> List[Dict[str, Any]]:
        filename = f"{match_id}.json"
        return self.fetch_json("lineups", filename)

    def events(self, match_id: int) -> List[Dict[str, Any]]:
        filename = f"{match_id}.json"
        return self.fetch_json("events", filename)


def role_from_position(position: str) -> str:
    if not position:
        return "other"
    pos = position.lower()
    if "goalkeeper" in pos:
        return "goalkeeper"
    if "wing back" in pos or "full back" in pos or pos.endswith(" back"):
        return "fullback"
    if "center back" in pos or "centre back" in pos or pos == "cb" or "sweeper" in pos:
        return "center_back"
    if "midfield" in pos or "pivot" in pos or "holding" in pos:
        return "midfield_pivot"
    if "wing" in pos and "wing back" not in pos:
        return "wide_forward"
    if "forward" in pos or "striker" in pos or "attacker" in pos:
        if "wing" in pos:
            return "wide_forward"
        return "striker"
    if "attacking" in pos:
        return "midfield_pivot"
    return "other"


def build_player_role_map(lineups: List[Dict[str, Any]]) -> Dict[int, Dict[int, str]]:
    mapping: Dict[int, Dict[int, str]] = {}
    for team in lineups:
        team_id = team.get("team_id")
        if team_id is None:
            continue
        players = {}
        for player in team.get("lineup", []):
            pid = player.get("player_id")
            if pid is None:
                continue
            positions = player.get("positions") or []
            if not positions:
                continue
            primary = positions[0]
            position_name = primary.get("position") or ""
            role = role_from_position(position_name)
            players[pid] = role
        mapping[team_id] = players
    return mapping


def _ensure_role_dict() -> Dict[str, float]:
    return defaultdict(float)  # type: ignore[arg-type]


def compute_match_role_stats(
    match: Dict[str, Any],
    events: List[Dict[str, Any]],
    player_roles: Dict[int, Dict[int, str]],
) -> Dict[int, Dict[str, Dict[str, float]]]:
    home_id = (match.get("home_team") or {}).get("home_team_id")
    away_id = (match.get("away_team") or {}).get("away_team_id")
    if home_id is None or away_id is None:
        raise ValueError("Missing team identifiers in match metadata")

    offense_chain: Dict[int, Dict[str, float]] = {
        home_id: _ensure_role_dict(),
        away_id: _ensure_role_dict(),
    }
    offense_shots: Dict[int, Dict[str, float]] = {
        home_id: _ensure_role_dict(),
        away_id: _ensure_role_dict(),
    }
    defense_xga: Dict[int, Dict[str, float]] = {
        home_id: _ensure_role_dict(),
        away_id: _ensure_role_dict(),
    }
    team_actual_xg: Dict[int, float] = defaultdict(float)

    possession_players: Dict[int, Dict[int, Set[int]]] = defaultdict(
        lambda: defaultdict(set)
    )

    for event in events:
        pos_id = event.get("possession")
        if pos_id is None:
            continue
        team = (event.get("team") or {}).get("id")
        possession_team = (event.get("possession_team") or {}).get("id")
        player = (event.get("player") or {}).get("id")
        if (
            team is not None
            and possession_team is not None
            and team == possession_team
            and player is not None
        ):
            possession_players[pos_id][team].add(player)

    for event in events:
        if (event.get("type") or {}).get("name") != "Shot":
            continue
        xg = ((event.get("shot") or {}).get("statsbomb_xg"))
        if xg is None:
            continue
        team_id = (event.get("team") or {}).get("id")
        shooter_id = (event.get("player") or {}).get("id")
        possession_id = event.get("possession")
        if team_id is None or possession_id is None:
            continue

        opponent_id = home_id if team_id == away_id else away_id
        shooter_role = (
            player_roles.get(team_id, {}).get(shooter_id, "other")
        )
        offense_shots[team_id][shooter_role] += xg
        defense_role = DEFENSE_TARGET_MAP.get(shooter_role, "midfield_pivot")
        defense_xga[opponent_id][defense_role] += xg
        team_actual_xg[team_id] += xg

        players = set(possession_players.get(possession_id, {}).get(team_id, set()))
        if shooter_id is not None:
            players.add(shooter_id)
        if not players:
            continue
        share = xg / len(players)
        for pid in players:
            role = player_roles.get(team_id, {}).get(pid, "other")
            offense_chain[team_id][role] += share

    return {
        home_id: {
            "offense_chain": dict(offense_chain[home_id]),
            "offense_shots": dict(offense_shots[home_id]),
            "defense_xga": dict(defense_xga[home_id]),
            "actual_xg": team_actual_xg.get(home_id, 0.0),
        },
        away_id: {
            "offense_chain": dict(offense_chain[away_id]),
            "offense_shots": dict(offense_shots[away_id]),
            "defense_xga": dict(defense_xga[away_id]),
            "actual_xg": team_actual_xg.get(away_id, 0.0),
        },
    }


def ensure_team_entry(team_stats: Dict[int, Dict[str, Any]], team_id: int, name: str) -> Dict[str, Any]:
    if team_id not in team_stats:
        team_stats[team_id] = {
            "name": name,
            "offense": {role: RoleSplit() for role in ROLES},
            "defense": {role: RoleSplit() for role in ROLES},
            "matches_played": 0,
        }
    return team_stats[team_id]


def update_team_stats(
    team_stats: Dict[int, Dict[str, Any]],
    team_id: int,
    team_name: str,
    role_stats: Dict[str, Dict[str, float]],
) -> None:
    entry = ensure_team_entry(team_stats, team_id, team_name)
    entry["matches_played"] += 1

    offense = entry["offense"]
    defense = entry["defense"]

    for role in ROLES:
        offense[role].bump_matches()
        offense_value = role_stats.get("offense_chain", {}).get(role, 0.0)
        offense[role].add(offense_value)

        defense[role].bump_matches()
        defense_value = role_stats.get("defense_xga", {}).get(role, 0.0)
        defense[role].add(defense_value)


def compute_role_averages(entry: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, float]]:
    offense_avg = {role: entry["offense"][role].average() for role in ROLES}
    defense_avg = {role: entry["defense"][role].average() for role in ROLES}
    return offense_avg, defense_avg


def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def load_matches(
    client: StatsBombClient,
    competition_filter: Optional[Set[int]],
    match_limit: Optional[int],
) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    competitions = client.competitions()
    for comp in competitions:
        comp_id = comp["competition_id"]
        if competition_filter and comp_id not in competition_filter:
            continue
        season_id = comp["season_id"]
        try:
            comp_matches = client.matches(comp_id, season_id)
        except RuntimeError as exc:
            logging.warning("Skipping competition %s/%s: %s", comp_id, season_id, exc)
            continue
        for match in comp_matches:
            match_copy = dict(match)
            match_copy["competition_id"] = comp_id
            match_copy["competition_name"] = comp.get("competition_name")
            match_copy["season_id"] = season_id
            match_copy["season_name"] = comp.get("season_name")
            matches.append(match_copy)
        if match_limit and len(matches) >= match_limit:
            break

    matches.sort(
        key=lambda m: (
            m.get("match_date") or "9999-12-31",
            m.get("match_id", 0),
        )
    )
    if match_limit:
        matches = matches[:match_limit]
    return matches


def evaluate_match(
    match: Dict[str, Any],
    role_stats: Dict[int, Dict[str, Dict[str, float]]],
    team_stats: Dict[int, Dict[str, Any]],
    min_matches: int,
    threshold: float,
) -> Optional[Dict[str, Any]]:
    home_meta = match.get("home_team") or {}
    away_meta = match.get("away_team") or {}
    home_id = home_meta.get("home_team_id")
    away_id = away_meta.get("away_team_id")
    if home_id is None or away_id is None:
        return None

    home_entry = team_stats.get(home_id)
    away_entry = team_stats.get(away_id)
    if (
        not home_entry
        or not away_entry
        or home_entry["matches_played"] < min_matches
        or away_entry["matches_played"] < min_matches
    ):
        return None

    home_off, home_def = compute_role_averages(home_entry)
    away_off, away_def = compute_role_averages(away_entry)

    home_combined = sum(home_off[role] - away_def[role] for role in ROLES)
    away_combined = sum(away_off[role] - home_def[role] for role in ROLES)
    net_delta = home_combined - away_combined

    if net_delta >= threshold:
        bet_side = "home"
    elif net_delta <= -threshold:
        bet_side = "away"
    else:
        return None

    home_score = match.get("home_score")
    away_score = match.get("away_score")

    if bet_side == "home":
        success = (home_score is not None and away_score is not None and home_score > away_score)
        predicted_team = home_meta.get("home_team_name")
    else:
        success = (home_score is not None and away_score is not None and away_score > home_score)
        predicted_team = away_meta.get("away_team_name")

    return {
        "match_id": match.get("match_id"),
        "match_date": match.get("match_date"),
        "competition": match.get("competition_name"),
        "season": match.get("season_name"),
        "home_team": home_meta.get("home_team_name"),
        "away_team": away_meta.get("away_team_name"),
        "home_score": home_score,
        "away_score": away_score,
        "home_combined_delta": home_combined,
        "away_combined_delta": away_combined,
        "net_delta": net_delta,
        "bet_side": bet_side,
        "predicted_team": predicted_team,
        "success": success,
        "actual_home_xg": role_stats.get(home_id, {}).get("actual_xg", 0.0),
        "actual_away_xg": role_stats.get(away_id, {}).get("actual_xg", 0.0),
    }


def backtest(
    client: StatsBombClient,
    matches: List[Dict[str, Any]],
    min_matches: int,
    threshold: float,
    csv_path: Path,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    team_stats: Dict[int, Dict[str, Any]] = {}
    predictions: List[Dict[str, Any]] = []
    processed = 0
    skipped_no_data = 0

    for idx, match in enumerate(matches, start=1):
        match_id = match.get("match_id")
        try:
            lineups = client.lineups(match_id)
            events = client.events(match_id)
        except Exception as exc:  # pragma: no cover - network issues
            skipped_no_data += 1
            logging.warning("Skipping match %s due to data issue: %s", match_id, exc)
            continue

        player_roles = build_player_role_map(lineups)
        role_stats = compute_match_role_stats(match, events, player_roles)

        prediction = evaluate_match(match, role_stats, team_stats, min_matches, threshold)
        if prediction:
            predictions.append(prediction)

        home_meta = match.get("home_team") or {}
        away_meta = match.get("away_team") or {}
        home_id = home_meta.get("home_team_id")
        away_id = away_meta.get("away_team_id")
        if home_id is None or away_id is None:
            skipped_no_data += 1
            continue

        update_team_stats(team_stats, home_id, home_meta.get("home_team_name", ""), role_stats.get(home_id, {}))
        update_team_stats(team_stats, away_id, away_meta.get("away_team_name", ""), role_stats.get(away_id, {}))
        processed += 1

        if idx % 100 == 0:
            logging.info(
                "Processed %s/%s matches (bets: %s)",
                idx,
                len(matches),
                len(predictions),
            )

    if predictions:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "match_id",
                    "match_date",
                    "competition",
                    "season",
                    "home_team",
                    "away_team",
                    "home_score",
                    "away_score",
                    "home_combined_delta",
                    "away_combined_delta",
                    "net_delta",
                    "bet_side",
                    "predicted_team",
                    "success",
                    "actual_home_xg",
                    "actual_away_xg",
                ],
            )
            writer.writeheader()
            for row in predictions:
                writer.writerow(row)

    wins = sum(1 for pred in predictions if pred["success"])
    summary = {
        "matches_consumed": processed,
        "bets_placed": len(predictions),
        "bet_wins": wins,
        "bet_losses": len(predictions) - wins,
        "win_rate": (wins / len(predictions)) if predictions else 0.0,
        "skipped_matches": skipped_no_data + (len(matches) - processed - skipped_no_data),
    }

    return predictions, summary


def lookup_team(team_stats: Dict[int, Dict[str, Any]], name: str) -> Optional[Tuple[int, Dict[str, Any]]]:
    lowered = name.strip().lower()
    for team_id, entry in team_stats.items():
        if entry.get("name", "").strip().lower() == lowered:
            return team_id, entry
    return None


def single_match_delta(
    team_a: str,
    team_b: str,
    team_stats: Dict[int, Dict[str, Any]],
    threshold: float,
) -> Dict[str, Any]:
    lookup_a = lookup_team(team_stats, team_a)
    lookup_b = lookup_team(team_stats, team_b)
    if not lookup_a or not lookup_b:
        missing = []
        if not lookup_a:
            missing.append(team_a)
        if not lookup_b:
            missing.append(team_b)
        raise ValueError(f"Teams not found in historical data: {', '.join(missing)}")

    team_a_id, entry_a = lookup_a
    team_b_id, entry_b = lookup_b

    off_a, def_a = compute_role_averages(entry_a)
    off_b, def_b = compute_role_averages(entry_b)
    combined_a = sum(off_a[role] - def_b[role] for role in ROLES)
    combined_b = sum(off_b[role] - def_a[role] for role in ROLES)
    net_delta = combined_a - combined_b

    if net_delta >= threshold:
        suggestion = team_a
    elif net_delta <= -threshold:
        suggestion = team_b
    else:
        suggestion = None

    return {
        "team_a": team_a,
        "team_b": team_b,
        "team_a_offense": off_a,
        "team_b_offense": off_b,
        "team_a_defense": def_a,
        "team_b_defense": def_b,
        "combined_a": combined_a,
        "combined_b": combined_b,
        "net_delta": net_delta,
        "suggested_team": suggestion,
    }


def hydrate_team_stats(
    client: StatsBombClient,
    matches: List[Dict[str, Any]],
    min_matches: int,
) -> Dict[int, Dict[str, Any]]:
    """Process matches purely to build up historical team stats."""
    team_stats: Dict[int, Dict[str, Any]] = {}
    for match in matches:
        match_id = match.get("match_id")
        try:
            lineups = client.lineups(match_id)
            events = client.events(match_id)
        except Exception as exc:  # pragma: no cover
            logging.warning("Skipping match %s during hydration: %s", match_id, exc)
            continue

        player_roles = build_player_role_map(lineups)
        role_stats = compute_match_role_stats(match, events, player_roles)

        home_meta = match.get("home_team") or {}
        away_meta = match.get("away_team") or {}
        home_id = home_meta.get("home_team_id")
        away_id = away_meta.get("away_team_id")
        if home_id is None or away_id is None:
            continue

        update_team_stats(team_stats, home_id, home_meta.get("home_team_name", ""), role_stats.get(home_id, {}))
        update_team_stats(team_stats, away_id, away_meta.get("away_team_name", ""), role_stats.get(away_id, {}))

    # Filter teams below min_matches to ensure averages are representative
    return {
        tid: entry
        for tid, entry in team_stats.items()
        if entry["matches_played"] >= min_matches
    }


def configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute role-based xG deltas and backtest wagering edges using StatsBomb data.",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/statsbomb",
        help="Directory for caching StatsBomb open-data files (default: %(default)s)",
    )
    parser.add_argument(
        "--competitions",
        nargs="*",
        type=int,
        help="Optional list of competition IDs to include (default: all)",
    )
    parser.add_argument(
        "--matches-limit",
        type=int,
        default=None,
        help="Maximum number of matches to ingest (after filtering competitions)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="xG swing threshold to trigger bets (default: %(default)s)",
    )
    parser.add_argument(
        "--min-matches",
        type=int,
        default=DEFAULT_MIN_MATCHES,
        help="Minimum historical matches per team before producing deltas",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest_parser = subparsers.add_parser(
        "backtest",
        help="Run a historical backtest and export wager accuracy",
    )
    backtest_parser.add_argument(
        "--output-csv",
        default="outputs/soccer_xg_delta_backtest.csv",
        help="Path for exported CSV of triggered bets",
    )

    single_parser = subparsers.add_parser(
        "single",
        help="Compute delta between two specific teams using accumulated history",
    )
    single_parser.add_argument("team_a", help="Name of first team (e.g., Manchester City)")
    single_parser.add_argument("team_b", help="Name of second team (e.g., Aston Villa)")

    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    cache_dir = Path(args.cache_dir).expanduser()
    client = StatsBombClient(cache_dir=cache_dir)

    competitions = set(args.competitions) if args.competitions else None
    matches = load_matches(client, competitions, args.matches_limit)
    if not matches:
        logging.error("No matches found for the provided configuration")
        return 1

    if args.command == "backtest":
        csv_path = Path(args.output_csv)
        _, summary = backtest(
            client,
            matches,
            min_matches=args.min_matches,
            threshold=args.threshold,
            csv_path=csv_path,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "single":
        team_stats = hydrate_team_stats(
            client,
            matches,
            min_matches=args.min_matches,
        )
        if not team_stats:
            logging.error("No team stats available; try lowering --min-matches or expanding competitions")
            return 1
        result = single_match_delta(
            args.team_a,
            args.team_b,
            team_stats,
            threshold=args.threshold,
        )
        print(json.dumps(result, indent=2))
        return 0

    logging.error("Unsupported command: %s", args.command)
    return 1


if __name__ == "__main__":
    sys.exit(main())
