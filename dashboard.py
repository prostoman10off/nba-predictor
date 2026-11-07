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

# Разница вероятностей в процентных пунктах,
# начиная с которой включается жёлтое выделение.
STRONG_FAVORITE_GAP = 30.0


CSS = """
<style>
.stApp {
    background: linear-gradient(
        135deg,
        #eaf5ff 0%,
        #e7f7ef 55%,
        #eff9ff 100%
    );
    color: #173b49;
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.6rem;
    padding-bottom: 2rem;
}

.hero {
    margin-bottom: 10px;
}

.hero h1 {
    color: #153e50;
    font-size: clamp(1.5rem, 3vw, 2.1rem);
    line-height: 1.2;
    margin: 0 0 6px;
    padding: 0;
}

.hero p {
    color: #526e79;
    font-size: 0.9rem;
    margin: 0;
}

.day-title {
    color: #234f60;
    font-size: 1rem;
    font-weight: 750;
    margin: 18px 0 10px;
}

/* Три карточки в ряд на широком экране. */
.matches-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    align-items: stretch;
}

.match-card {
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #d5e8e9;
    border-radius: 18px;
    padding: 12px;
    box-shadow: 0 5px 18px rgba(32, 90, 100, 0.06);
    min-width: 0;
}

.match-time {
    text-align: center;
    color: #56727d;
    font-size: 0.78rem;
    line-height: 1.3;
    margin-bottom: 8px;
}

.match-teams {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 22px minmax(0, 1fr);
    align-items: stretch;
    gap: 4px;
}

.team {
    text-align: center;
    border-radius: 12px;
    border: 1px solid transparent;
    padding: 8px 4px;
    min-width: 0;
}

.team.favorite {
    background: #edf9f3;
    border-color: #bee5cf;
}

/* Сильный фаворит: тёмно-жёлтые акценты. */
.team.strong-favorite {
    background: #fff0bb;
    border-color: #c99312;
    box-shadow: inset 0 0 0 1px rgba(201, 147, 18, 0.12);
}

.team-role {
    color: #637e87;
    font-size: 0.7rem;
    line-height: 1.3;
    margin-bottom: 5px;
}

.team-logo {
    width: 48px;
    height: 48px;
    object-fit: contain;
    display: block;
    margin: 0 auto 5px;
}

.logo-placeholder {
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.9rem;
    margin-bottom: 5px;
}

.team-name {
    font-size: 0.83rem;
    font-weight: 400;
    color: #234653;
    min-height: 36px;
    line-height: 1.2;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow-wrap: anywhere;
}

.team-probability {
    font-size: 1.65rem;
    font-weight: 400;
    color: #234653;
    line-height: 1.15;
    margin-top: 5px;
    white-space: nowrap;
}

.favorite .team-name,
.favorite .team-probability {
    font-weight: 800;
    color: #13744d;
}

.strong-favorite .team-name,
.strong-favorite .team-probability {
    font-weight: 800;
    color: #8a5900;
}

.fire {
    display: inline-block;
    margin-left: 3px;
    font-size: 1.1rem;
    vertical-align: middle;
}

.probability-label {
    font-size: 0.62rem;
    color: #69818a;
    margin-top: 3px;
    line-height: 1.2;
}

.versus {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    color: #89a2ab;
}

.probability-bar {
    display: flex;
    height: 5px;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 10px;
    background: #d9eaf5;
}

.bar-segment {
    height: 100%;
}

.bar-home {
    background: #73cba4;
}

.bar-away {
    background: #97c6e3;
}

.bar-strong {
    background: #c99312;
}

.page-note {
    color: #5c7882;
    font-size: 0.75rem;
    line-height: 1.55;
    margin-top: 20px;
}

.legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    font-size: 0.76rem;
    color: #526e79;
    margin: 8px 0 12px;
}

.legend-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 3px;
    display: inline-block;
}

.legend-green {
    background: #73cba4;
}

.legend-yellow {
    background: #c99312;
}

/* Планшеты и небольшие окна. */
@media (max-width: 1050px) {
    .matches-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

/* Телефоны. */
@media (max-width: 600px) {
    .block-container {
        padding-top: 1.2rem;
        padding-left: 12px;
        padding-right: 12px;
    }

    .matches-grid {
        grid-template-columns: minmax(0, 1fr);
        gap: 10px;
    }

    .match-card {
        padding: 12px;
    }

    .team-logo {
        width: 52px;
        height: 52px;
    }

    .team-name {
        font-size: 0.9rem;
    }

    .team-probability {
        font-size: 1.8rem;
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


def team_html(
    name,
    team_id,
    percent,
    favorite,
    strong_favorite,
    home,
):
    safe_name = html.escape(str(name), quote=True)
    role = "🏠 Хозяева" if home else "✈️ Гости"

    classes = ["team"]

    if favorite:
        classes.append("favorite")

    if strong_favorite:
        classes.append("strong-favorite")

    css_class = " ".join(classes)

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

    fire = ""

    if strong_favorite:
        fire = (
            '<span class="fire" '
            'title="Разница вероятностей не менее 30 п.п." '
            'aria-label="Сильный фаворит">🔥</span>'
        )

    return (
        f'<div class="{css_class}">'
        f'<div class="team-role">{role}</div>'
        f'{logo}'
        f'<div class="team-name">{safe_name}</div>'
        f'<div class="team-probability">'
        f'{percent:.1f}%{fire}'
        '</div>'
        '<div class="probability-label">вероятность победы</div>'
        '</div>'
    )


def match_html(forecast, game):
    local_start = parse_time(
        forecast["starts_at"]
    ).astimezone(LOCAL_TZ)

    home_probability = float(forecast["home_probability"])

    home_percent = round(home_probability * 100, 1)
    away_percent = round(100 - home_percent, 1)

    # Выделяем обычного фаворита по отображаемым процентам.
    home_favorite = home_percent > away_percent
    away_favorite = away_percent > home_percent

    # Порог считаем по исходной, неокруглённой вероятности.
    gap = abs(2 * home_probability - 1) * 100

    strong = gap >= STRONG_FAVORITE_GAP - 1e-9

    home_strong = strong and home_favorite
    away_strong = strong and away_favorite

    home_card = team_html(
        name=forecast["home_name"],
        team_id=game.get("home_id"),
        percent=home_percent,
        favorite=home_favorite,
        strong_favorite=home_strong,
        home=True,
    )

    away_card = team_html(
        name=forecast["away_name"],
        team_id=game.get("away_id"),
        percent=away_percent,
        favorite=away_favorite,
        strong_favorite=away_strong,
        home=False,
    )

    home_bar_class = (
        "bar-segment bar-strong"
        if home_strong
        else "bar-segment bar-home"
    )

    away_bar_class = (
        "bar-segment bar-strong"
        if away_strong
        else "bar-segment bar-away"
    )

    return (
        '<article class="match-card">'
        '<div class="match-time">'
        f'🕒 {local_start:%H:%M} · Новосибирск'
        '</div>'
        '<div class="match-teams">'
        f'{home_card}'
        '<div class="versus">VS</div>'
        f'{away_card}'
        '</div>'
        '<div class="probability-bar">'
        f'<div class="{home_bar_class}" '
        f'style="width:{home_percent}%"></div>'
        f'<div class="{away_bar_class}" '
        f'style="width:{away_percent}%"></div>'
        '</div>'
        '</article>'
    )


def main():
    st.set_page_config(
        page_title="NBA — прогнозы",
        page_icon="🏀",
        layout="wide",
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
        "по Новосибирску · Плановое обновление раз в 6 часов"
    )

    if now - updated_at > timedelta(hours=8):
        st.warning(
            "Обновлений не было более 8 часов. "
            "Расписание и вероятности могут быть устаревшими."
        )

    st.markdown(
        '<div class="legend">'
        '<span class="legend-item">'
        '<span class="legend-dot legend-green"></span>'
        'Фаворит модели'
        '</span>'
        '<span class="legend-item">'
        '<span class="legend-dot legend-yellow"></span>'
        '🔥 Разница вероятностей ≥ 30 п.п.'
        '</span>'
        '</div>',
        unsafe_allow_html=True,
    )

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

    # Группируем матчи по новосибирской дате.
    grouped = {}

    for forecast in upcoming:
        local_day = parse_time(
            forecast["starts_at"]
        ).astimezone(LOCAL_TZ).date()

        grouped.setdefault(local_day, []).append(forecast)

    for local_day, day_forecasts in grouped.items():
        st.markdown(
            '<div class="day-title">'
            f'📅 {local_day:%d.%m.%Y}'
            '</div>',
            unsafe_allow_html=True,
        )

        cards = []

        for forecast in day_forecasts:
            game = games_by_id.get(
                str(forecast["game_id"]),
                {},
            )

            cards.append(match_html(forecast, game))

        # Вся сетка выводится одним HTML-блоком,
        # чтобы карточки располагались в одном ряду.
        st.markdown(
            '<div class="matches-grid">'
            + "".join(cards)
            + '</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="page-note">'
        '🏠 Хозяева · ✈️ Гости. '
        'Фаворит выделен жирным. При разнице вероятностей '
        'от 30 процентных пунктов фаворит отмечен '
        'тёмно-жёлтым цветом и значком 🔥. '
        'Это порог модели, а не гарантия победы.<br><br>'
        'Прогноз учитывает возможный овертайм. '
        'Модель: Elo с поправкой на домашнюю площадку. '
        'Травмы, составы и отдых не учитываются. '
        'Вероятности пока не прошли проверку калибровки. '
        'Данные и логотипы: ESPN.'
        '</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
