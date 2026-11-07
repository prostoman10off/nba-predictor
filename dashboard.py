import html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st


REPOSITORY = "prostoman10off/nba-predictor"

BASE_URL = (
    f"https://raw.githubusercontent.com/{REPOSITORY}"
    "/refs/heads/main/data"
)

LOCAL_TZ = ZoneInfo("Asia/Novosibirsk")


CSS = """
<style>
.stApp {
    background: linear-gradient(
        135deg,
        #eaf5ff 0%,
        #e8f8f2 55%,
        #f3fbff 100%
    );
    color: #173b49;
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 900px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

.hero {
    margin-bottom: 18px;
}

.hero h1 {
    color: #153e50;
    font-size: clamp(1.8rem, 5vw, 2.6rem);
    margin-bottom: 6px;
}

.hero p {
    color: #526e79;
    margin: 0;
}

.day-title {
    color: #234f60;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 26px 0 12px;
}

.match-card {
    background: rgba(255, 255, 255, 0.93);
    border: 1px solid #d5e8e9;
    border-radius: 22px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(32, 90, 100, 0.07);
}

.match-time {
    text-align: center;
    color: #56727d;
    font-size: 0.88rem;
    margin-bottom: 16px;
}

.match-teams {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 38px minmax(0, 1fr);
    align-items: center;
    gap: 8px;
}

.team {
    text-align: center;
    border-radius: 16px;
    padding: 14px 8px;
    min-width: 0;
}

.team.favorite {
    background: #edf9f3;
    border: 1px solid #bde5cf;
}

.team-role {
    color: #637e87;
    font-size: 0.8rem;
    margin-bottom: 10px;
}

.team-logo {
    width: 76px;
    height: 76px;
    object-fit: contain;
    display: block;
    margin: 0 auto 10px;
}

.logo-placeholder {
    height: 76px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.5rem;
    margin-bottom: 10px;
}

.team-name {
    font-size: 1rem;
    font-weight: 400;
    color: #234653;
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow-wrap: anywhere;
    line-height: 1.3;
}

.team-probability {
    font-size: clamp(1.6rem, 5vw, 2.2rem);
    font-weight: 400;
    color: #234653;
    margin-top: 8px;
}

.favorite .team-name,
.favorite .team-probability {
    font-weight: 800;
    color: #13744d;
}

.probability-label {
    font-size: 0.72rem;
    color: #69818a;
    margin-top: 2px;
}

.versus {
    text-align: center;
    font-size: 0.8rem;
    font-weight: 700;
    color: #89a2ab;
}

.probability-bar {
    height: 7px;
    background: #d9eaf5;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 18px;
}

.probability-bar-home {
    height: 100%;
    background: #73cba4;
    border-radius: 20px;
}

.page-note {
    color: #5c7882;
    font-size: 0.8rem;
    line-height: 1.6;
    margin-top: 24px;
}

@media (max-width: 480px) {
    .block-container {
        padding-left: 12px;
        padding-right: 12px;
    }

    .match-card {
        padding: 14px 10px;
    }

    .match-teams {
        grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr);
        gap: 4px;
    }

    .team-logo {
        width: 60px;
        height: 60px;
    }

    .team-name {
        font-size: 0.88rem;
    }

    .team {
        padding: 12px 5px;
    }
}
</style>
"""


@st.cache_data(ttl=60)
def load_data():
    results = []

    with requests.Session() as session:
        for filename in (
            "metadata.json",
            "forecasts.json",
            "games.json",
        ):
            response = session.get(
                f"{BASE_URL}/{filename}",
                timeout=30,
            )
            response.raise_for_status()
            results.append(response.json())

    return tuple(results)


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def team_html(name, team_id, percent, favorite, home):
    safe_name = html.escape(name)
    role = "🏠 Хозяева" if home else "✈️ Гости"
    css_class = "team favorite" if favorite else "team"

    if team_id and str(team_id).isdigit():
        logo_url = (
            "https://a.espncdn.com/i/teamlogos/nba/500/"
            f"{team_id}.png"
        )

        logo = (
            f'<img class="team-logo" src="{logo_url}" '
            f'alt="Логотип {safe_name}" loading="lazy">'
        )
    else:
        logo = '<div class="logo-placeholder">🏀</div>'

    return (
        f'<div class="{css_class}">'
        f'<div class="team-role">{role}</div>'
        f'{logo}'
        f'<div class="team-name">{safe_name}</div>'
        f'<div class="team-probability">{percent:.1f}%</div>'
        '<div class="probability-label">вероятность победы</div>'
        '</div>'
    )


def main():
    st.set_page_config(
        page_title="NBA — прогнозы",
        page_icon="🏀",
        layout="centered",
    )

    st.markdown(CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="hero">'
        '<h1>🏀 NBA — прогнозы матчей</h1>'
        '<p>Ближайшие 48 часов · Новосибирск, UTC+7</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("↻ Обновить страницу"):
        load_data.clear()

    try:
        metadata, forecasts, games = load_data()
    except Exception:
        st.error(
            "Не удалось загрузить данные. "
            "Попробуйте обновить страницу позже."
        )
        return

    now = datetime.now(timezone.utc)
    updated_at = parse_time(metadata["updated_at"])
    local_updated = updated_at.astimezone(LOCAL_TZ)

    st.caption(
        f"Данные обновлены: {local_updated:%d.%m.%Y, %H:%M} "
        "по Новосибирску · Обновление раз в 6 часов"
    )

    if now - updated_at > timedelta(hours=8):
        st.warning(
            "Обновлений не было более 8 часов. "
            "Расписание и вероятности могут быть устаревшими."
        )

    # Match IDs let us find team IDs without changing
    # the existing updater or archived forecasts.
    games_by_id = {
        str(game["id"]): game
        for game in games
    }

    upcoming = [
        forecast
        for forecast in forecasts
        if now < parse_time(forecast["starts_at"])
        <= now + timedelta(hours=48)
    ]

    upcoming.sort(
        key=lambda forecast: parse_time(forecast["starts_at"])
    )

    if not upcoming:
        st.info(
            "В загруженных данных нет предстоящих матчей "
            "на ближайшие 48 часов."
        )

    current_day = None

    for forecast in upcoming:
        local_start = parse_time(
            forecast["starts_at"]
        ).astimezone(LOCAL_TZ)

        if current_day != local_start.date():
            current_day = local_start.date()

            st.markdown(
                f'<div class="day-title">'
                f'📅 {local_start:%d.%m.%Y}'
                f'</div>',
                unsafe_allow_html=True,
            )

        probability = forecast["home_probability"]
        home_percent = round(probability * 100, 1)
        away_percent = round(100 - home_percent, 1)

        game = games_by_id.get(
            str(forecast["game_id"]),
            {},
        )

        # Use displayed percentages to avoid visually
        # selecting a favorite when both show 50.0%.
        home_card = team_html(
            forecast["home_name"],
            game.get("home_id"),
            home_percent,
            home_percent > away_percent,
            home=True,
        )

        away_card = team_html(
            forecast["away_name"],
            game.get("away_id"),
            away_percent,
            away_percent > home_percent,
            home=False,
        )

        card = (
            '<div class="match-card">'
            f'<div class="match-time">'
            f'🕒 {local_start:%H:%M} · Новосибирск'
            '</div>'
            '<div class="match-teams">'
            f'{home_card}'
            '<div class="versus">VS</div>'
            f'{away_card}'
            '</div>'
            '<div class="probability-bar">'
            f'<div class="probability-bar-home" '
            f'style="width:{home_percent}%"></div>'
            '</div>'
            '</div>'
        )

        st.markdown(card, unsafe_allow_html=True)

    st.markdown(
        '<div class="page-note">'
        'Зелёным фоном и жирным шрифтом выделен фаворит модели. '
        'При равных процентах фаворит не выделяется.<br><br>'
        'Вероятности учитывают возможный овертайм. '
        'Используется экспериментальная модель Elo '
        'с поправкой на домашнюю площадку. '
        'Травмы, составы и отдых не учитываются. '
        'Проценты пока не прошли проверку калибровки '
        'и не гарантируют результат.<br>'
        'Данные и логотипы: ESPN.'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
