#!/usr/bin/env python3
"""Evaluate nba_delta.pl predictions against historical NBA results.

This script pulls game results from ESPN's public scoreboard API for a
date range, runs `nba_delta.pl` for each completed matchup (using
high-possessions lineups from pbpstats) and computes accuracy metrics.
"""

import argparse
import datetime as dt
import json
import math
import pathlib
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
PBP_BASE = "https://api.pbpstats.com/get-totals/nba"


TEAM_ID_MAP: Dict[str, str] = {
    "ATL": "1610612737",
    "BOS": "1610612738",
    "BKN": "1610612751",
    "BOS": "1610612738",
    "CHA": "1610612766",
    "CHI": "1610612741",
    "CLE": "1610612739",
    "DAL": "1610612742",
    "DEN": "1610612743",
    "DET": "1610612765",
    "GS": "1610612744",
    "GSW": "1610612744",
    "HOU": "1610612745",
    "IND": "1610612754",
    "LAC": "1610612746",
    "LAL": "1610612747",
    "MEM": "1610612763",
    "MIA": "1610612748",
    "MIL": "1610612749",
    "MIN": "1610612750",
    "NO": "1610612740",
    "NOP": "1610612740",
    "NY": "1610612752",
    "NYK": "1610612752",
    "OKC": "1610612760",
    "ORL": "1610612753",
    "PHI": "1610612755",
    "PHX": "1610612756",
    "POR": "1610612757",
    "SAC": "1610612758",
    "SA": "1610612759",
    "SAS": "1610612759",
    "TOR": "1610612761",
    "UTA": "1610612762",
    "UTAH": "1610612762",
    "WAS": "1610612764",
    "WSH": "1610612764",
}

SEASON_TYPE_MAP = {
    1: "Pre Season",
    2: "Regular Season",
    3: "Playoffs",
    4: "Playoffs",
    5: "Play-In",
}


@dataclass
class Lineup:
    entity_id: str
    name: str
    off_poss: float
    def_poss: float


@dataclass
class GameResult:
    event_id: str
    date: str
    matchup: str
    season: str
    season_type: str
    home_abbr: str
    away_abbr: str
    home_team_id: str
    away_team_id: str
    home_score: int
    away_score: int
    actual_margin: int
    predicted_delta: float
    baseline_delta: float
    slot_adjustments: Dict[str, float]

    @property
    def predicted_winner_home(self) -> bool:
        return self.predicted_delta >= 0

    @property
    def actual_winner_home(self) -> bool:
        return self.actual_margin >= 0


def fetch_url(url: str, *, retries: int = 3, sleep: float = 0.5) -> bytes:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:  # pragma: no cover - network handling
            if 500 <= exc.code < 600 and attempt + 1 < retries:
                time.sleep(sleep * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt + 1 < retries:
                time.sleep(sleep * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def fetch_scoreboard(date: dt.date) -> dict:
    params = urllib.parse.urlencode({"dates": date.strftime("%Y%m%d")})
    data = fetch_url(f"{ESPN_SCOREBOARD}?{params}")
    return json.loads(data.decode("utf-8"))


def extract_completed_games(scoreboard_payload: dict) -> List[dict]:
    games = []
    for event in scoreboard_payload.get("events", []):
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]
        season_info = event.get("season") or comp.get("season") or {}
        season_year = season_info.get("year")
        season_type_id = season_info.get("type")
        status = comp.get("status") or event.get("status") or {}
        stype = status.get("type") or {}
        if stype.get("completed") is not True:
            continue
        competitors = comp.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if not home or not away:
            continue
        try:
            home_score = int(home.get("score"))
            away_score = int(away.get("score"))
        except (TypeError, ValueError):
            continue
        games.append({
            "event_id": event.get("id"),
            "date": event.get("date"),
            "matchup": event.get("name"),
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "season_year": season_year,
            "season_type_id": season_type_id,
        })
    return games


def fetch_top_lineup(team_id: str, season: str, season_type: str, min_poss: int,
                     cache: Dict[Tuple[str, str, str, int], Lineup]) -> Lineup:
    cache_key: Tuple[str, str, str, int] = (team_id, season, season_type, min_poss)
    if cache_key in cache:
        return cache[cache_key]

    params = urllib.parse.urlencode({
        "Type": "Lineup",
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "Table": "Scoring",
        "MinimumPossessions": str(min_poss),
    })
    data = fetch_url(f"{PBP_BASE}?{params}")
    payload = json.loads(data.decode("utf-8"))
    rows = payload.get("multi_row_table_data") or []
    if not rows:
        raise RuntimeError(f"No lineup data for team {team_id}")
    top = max(rows, key=lambda r: r.get("OffPoss", 0))
    lineup = Lineup(
        entity_id=top["EntityId"],
        name=top.get("Name", ""),
        off_poss=float(top.get("OffPoss", 0)),
        def_poss=float(top.get("DefPoss", 0)),
    )
    cache[cache_key] = lineup
    return lineup


def run_nba_delta(team1_id: str, lineup1_id: str,
                  team2_id: str, lineup2_id: str,
                  season: str, season_type: str, min_poss: int) -> dict:
    cmd = [
        "perl",
        "nba_delta.pl",
        team1_id,
        lineup1_id,
        team2_id,
        lineup2_id,
        "--season", season,
        "--season-type", season_type,
        "--min-poss", str(min_poss),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(pathlib.Path(__file__).resolve().parent.parent), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"nba_delta.pl failed ({result.returncode}): {result.stderr or result.stdout}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from nba_delta.pl: {exc}: {result.stdout}")


def format_season(year: Optional[int], fallback_date: dt.date) -> str:
    if year is None:
        year = fallback_date.year + (1 if fallback_date.month >= 7 else 0)
    return f"{year - 1}-{str(year)[-2:]}"


def season_type_name(type_id: Optional[int]) -> str:
    if type_id is None:
        return "Regular Season"
    return SEASON_TYPE_MAP.get(type_id, "Regular Season")


def evaluate(date_start: dt.date, date_end: dt.date,
             season_override: Optional[str], season_type_override: Optional[str],
             min_poss: int, max_games: Optional[int] = None) -> Dict[str, object]:
    lineup_cache: Dict[Tuple[str, str, str, int], Lineup] = {}
    results: List[GameResult] = []

    current = date_start
    processed = 0
    while current <= date_end:
        scoreboard = fetch_scoreboard(current)
        for game in extract_completed_games(scoreboard):
            if max_games is not None and processed >= max_games:
                break

            home_team = game["home"].get("team", {})
            away_team = game["away"].get("team", {})
            home_abbr = home_team.get("abbreviation")
            away_abbr = away_team.get("abbreviation")
            if home_abbr not in TEAM_ID_MAP or away_abbr not in TEAM_ID_MAP:
                continue

            home_id = TEAM_ID_MAP[home_abbr]
            away_id = TEAM_ID_MAP[away_abbr]
            game_date = dt.date.fromisoformat(game["date"][0:10]) if game.get("date") else current
            season_str = season_override or format_season(game.get("season_year"), game_date)
            season_type = season_type_override or season_type_name(game.get("season_type_id"))
            try:
                home_lineup = fetch_top_lineup(home_id, season_str, season_type, min_poss, lineup_cache)
                away_lineup = fetch_top_lineup(away_id, season_str, season_type, min_poss, lineup_cache)
            except Exception as exc:
                # Skip games without lineup data
                print(f"Skipping {game['matchup']} ({current}): lineup fetch failed: {exc}", file=sys.stderr)
                continue

            try:
                output = run_nba_delta(home_id, home_lineup.entity_id,
                                       away_id, away_lineup.entity_id,
                                       season_str, season_type, min_poss)
            except Exception as exc:
                print(f"Skipping {game['matchup']} ({current}): {exc}", file=sys.stderr)
                continue

            result = GameResult(
                event_id=game["event_id"],
                date=game["date"],
                matchup=game["matchup"],
                season=season_str,
                season_type=season_type,
                home_abbr=home_abbr,
                away_abbr=away_abbr,
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=game["home_score"],
                away_score=game["away_score"],
                actual_margin=game["home_score"] - game["away_score"],
                predicted_delta=float(output.get("final_delta", 0.0)),
                baseline_delta=float(output.get("baseline_delta", 0.0)),
                slot_adjustments={k: float(v) for k, v in (output.get("slot_adjustments") or {}).items()},
            )
            results.append(result)
            processed += 1
        current += dt.timedelta(days=1)
    if not results:
        raise RuntimeError("No games evaluated")

    predicted = [r.predicted_delta for r in results]
    actual = [r.actual_margin for r in results]
    winner_correct = sum(1 for r in results if r.predicted_winner_home == r.actual_winner_home)
    accuracy = winner_correct / len(results)
    mae = statistics.fmean(abs(p - a) for p, a in zip(predicted, actual))
    mse = statistics.fmean((p - a) ** 2 for p, a in zip(predicted, actual))
    rmse = math.sqrt(mse)
    correlation = statistics.correlation(predicted, actual) if len(results) > 1 else float('nan')

    summary = {
        "games_evaluated": len(results),
        "winner_accuracy": accuracy,
        "winner_correct": winner_correct,
        "winner_incorrect": len(results) - winner_correct,
        "mean_absolute_error": mae,
        "root_mean_squared_error": rmse,
        "pearson_correlation": correlation,
        "date_start": date_start.isoformat(),
        "date_end": date_end.isoformat(),
        "season_override": season_override,
        "season_type_override": season_type_override,
        "min_poss": min_poss,
    }

    summary_path = pathlib.Path("nba_delta_accuracy_summary.json")
    details_path = pathlib.Path("nba_delta_accuracy_details.json")
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with details_path.open("w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in results], f, indent=2)

    return summary


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate nba_delta.pl accuracy over historical games")
    parser.add_argument("--season", default=None, help="Override season string passed to pbpstats (e.g. 2024-25). Defaults to auto per game.")
    parser.add_argument("--season-type", default=None, help="Override season type (e.g. Regular Season, Playoffs). Defaults to auto per game.")
    parser.add_argument("--min-poss", type=int, default=50, help="Minimum possessions filter for pbpstats (default: 50)")
    parser.add_argument("--start", default="2025-10-01", help="Start date (inclusive) in YYYY-MM-DD")
    parser.add_argument("--end", default=dt.date.today().isoformat(), help="End date (inclusive) in YYYY-MM-DD")
    parser.add_argument("--max-games", type=int, help="Optional cap on number of games to evaluate")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    date_start = dt.date.fromisoformat(args.start)
    date_end = dt.date.fromisoformat(args.end)
    if date_end < date_start:
        raise SystemExit("--end must be on or after --start")
    summary = evaluate(date_start, date_end, args.season, args.season_type,
                       args.min_poss, args.max_games)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
