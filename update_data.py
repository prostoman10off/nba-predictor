import truststore

truststore.inject_into_ssl()

import json
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

START_DATE = date(2026, 10, 20)
SEASON_YEAR = 2027

INITIAL_ELO = 1500.0
K = 20.0
HOME_ADVANTAGE = 60.0

NBA_TZ = ZoneInfo("America/New_York")

MODEL_VERSION = (
    f"elo-v1;start={START_DATE};initial={INITIAL_ELO};"
    f"k={K};home={HOME_ADVANTAGE}"
)

API_URL = (
    "https://site.api.espn.com/apis/site/v2/"
    "sports/basketball/nba/scoreboard"
)

EXCLUDED_STATUSES = {
    "STATUS_POSTPONED",
    "STATUS_CANCELED",
    "STATUS_CANCELLED",
    "STATUS_SUSPENDED",
}


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def read_json(name, default):
    path = DATA / name

    if not path.exists():
        return default

    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(name, value):
    destination = DATA / name
    temporary = destination.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    temporary.replace(destination)


def probability(home_elo, away_elo, neutral):
    advantage = 0 if neutral else HOME_ADVANTAGE
    difference = home_elo + advantage - away_elo

    return 1 / (1 + 10 ** (-difference / 400))


def make_session():
    session = requests.Session()

    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry),
    )

    session.headers.update({
        "User-Agent": "NBA-Forecast-Updater/1.0",
        "Accept": "application/json",
    })

    return session


def parse_event(event, fallback_season):
    event_id = str(event["id"])

    season = event.get("season") or fallback_season
    year = season.get("year")
    season_type = season.get("type")

    if isinstance(season_type, dict):
        season_type = season_type.get("id")

    if year is None or season_type is None:
        raise ValueError(
            f"Missing season information: {event_id}"
        )

    if int(year) != SEASON_YEAR:
        return None

    if int(season_type) not in (2, 3):
        return None

    competition = event["competitions"][0]
    competitors = competition["competitors"]

    home = next(
        item for item in competitors
        if item["homeAway"] == "home"
    )

    away = next(
        item for item in competitors
        if item["homeAway"] == "away"
    )

    start = parse_time(
        competition.get("date") or event["date"]
    )

    if start.astimezone(NBA_TZ).date() < START_DATE:
        return None

    status = (
        competition.get("status")
        or event.get("status")
        or {}
    ).get("type", {})

    if "completed" not in status:
        raise ValueError(
            f"Missing completion status: {event_id}"
        )

    completed = bool(status["completed"])
    home_score = None
    away_score = None

    if completed:
        home_score = int(home["score"])
        away_score = int(away["score"])

        if home_score == away_score:
            raise ValueError(
                f"Tied final score: {event_id}"
            )

    return {
        "id": event_id,
        "start": start.isoformat(),
        "home_id": str(home["team"]["id"]),
        "home_name": home["team"]["displayName"],
        "away_id": str(away["team"]["id"]),
        "away_name": away["team"]["displayName"],
        "home_score": home_score,
        "away_score": away_score,
        "completed": completed,
        "neutral": bool(competition.get("neutralSite", False)),
        "state": status.get("state", ""),
        "status": status.get("name", ""),
    }


def main():
    DATA.mkdir(parents=True, exist_ok=True)

    games = read_json("games.json", [])
    archive = read_json("archive.json", [])
    metadata = read_json("metadata.json", {})

    by_id = {
        str(game["id"]): game
        for game in games
    }

    today = datetime.now(NBA_TZ).date()

    # Once a week, reload the whole period to catch
    # corrections to older results.
    full_refresh = (
        not metadata.get("updated_at")
        or today.weekday() == 6
    )

    if full_refresh:
        first_day = START_DATE
    else:
        previous_day = (
            parse_time(metadata["updated_at"])
            .astimezone(NBA_TZ)
            .date()
        )

        first_day = max(
            START_DATE,
            min(today, previous_day) - timedelta(days=7),
        )

    last_day = today + timedelta(days=3)
    number_of_days = (last_day - first_day).days + 1

    if number_of_days <= 0:
        raise ValueError("The configured season starts in the future.")

    # No output files are changed until every request succeeds.
    with make_session() as session:
        for index in range(number_of_days):
            day = first_day + timedelta(days=index)

            print(
                f"Fetching {day}: "
                f"{index + 1}/{number_of_days}",
                flush=True,
            )

            response = session.get(
                API_URL,
                params={
                    "dates": day.strftime("%Y%m%d"),
                    "limit": 1000,
                },
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            if not isinstance(data.get("events"), list):
                raise ValueError(
                    f"Unexpected ESPN response for {day}"
                )

            for event in data["events"]:
                game = parse_event(
                    event,
                    data.get("season") or {},
                )

                if game is not None:
                    by_id[game["id"]] = game

            time.sleep(0.3)

    games = sorted(
        by_id.values(),
        key=lambda game: (game["start"], game["id"]),
    )

    ratings = {}
    counts = {}
    completed_count = 0

    now = datetime.now(timezone.utc)

    for game in games:
        home = game["home_id"]
        away = game["away_id"]

        for team_id in (home, away):
            ratings.setdefault(team_id, INITIAL_ELO)
            counts.setdefault(team_id, 0)

        if not game["completed"]:
            continue

        if parse_time(game["start"]) > now:
            continue

        predicted = probability(
            ratings[home],
            ratings[away],
            game["neutral"],
        )

        actual = float(
            game["home_score"] > game["away_score"]
        )

        change = K * (actual - predicted)

        ratings[home] += change
        ratings[away] -= change

        counts[home] += 1
        counts[away] += 1

        completed_count += 1

    # Preserve all previously archived probabilities.
    archived_ids = {
        str(item["game_id"])
        for item in archive
    }

    forecasts = []
    added = 0

    for game in games:
        start = parse_time(game["start"])
        saved_at = datetime.now(timezone.utc)

        if not saved_at < start <= saved_at + timedelta(hours=48):
            continue

        if game["completed"] or game["state"] != "pre":
            continue

        if game["status"] in EXCLUDED_STATUSES:
            continue

        home = game["home_id"]
        away = game["away_id"]

        predicted = probability(
            ratings[home],
            ratings[away],
            game["neutral"],
        )

        forecast = {
            "game_id": game["id"],
            "saved_at": saved_at.isoformat(),
            "source_sync": now.isoformat(),
            "starts_at": game["start"],
            "home_name": game["home_name"],
            "away_name": game["away_name"],
            "home_elo": ratings[home],
            "away_elo": ratings[away],
            "home_probability": predicted,
            "model_version": MODEL_VERSION,
        }

        forecasts.append(forecast)

        if game["id"] not in archived_ids:
            archive.append(dict(forecast))
            archived_ids.add(game["id"])
            added += 1

    archive.sort(
        key=lambda item: (item["starts_at"], item["game_id"])
    )

    metadata = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "games_count": len(games),
        "completed_count": completed_count,
        "forecasts_count": len(forecasts),
        "archive_count": len(archive),
        "timezone": "Asia/Novosibirsk",
    }

    write_json("games.json", games)
    write_json("forecasts.json", forecasts)
    write_json("archive.json", archive)
    write_json("metadata.json", metadata)

    print()
    print("UPDATE OK")
    print("Games:", len(games))
    print("Completed games:", completed_count)
    print("Upcoming forecasts:", len(forecasts))
    print("New archived forecasts:", added)
    print("Total archived forecasts:", len(archive))


if __name__ == "__main__":
    main()
