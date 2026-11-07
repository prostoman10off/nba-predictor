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


@st.cache_data(ttl=60)
def load_data():
    with requests.Session() as session:
        metadata_response = session.get(
            f"{BASE_URL}/metadata.json",
            timeout=30,
        )
        metadata_response.raise_for_status()

        forecasts_response = session.get(
            f"{BASE_URL}/forecasts.json",
            timeout=30,
        )
        forecasts_response.raise_for_status()

        return (
            metadata_response.json(),
            forecasts_response.json(),
        )


def parse_time(value):
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).astimezone(timezone.utc)


def main():
    st.set_page_config(
        page_title="NBA — ближайшие матчи",
        page_icon="🏀",
        layout="centered",
    )

    st.title("🏀 NBA — ближайшие матчи")

    st.caption(
        "Вероятности победы с учётом овертайма · "
        "Ближайшие 48 часов · Время Новосибирска"
    )

    if st.button("Обновить страницу"):
        load_data.clear()

    try:
        metadata, forecasts = load_data()
    except Exception:
        st.error(
            "Не удалось загрузить прогнозы. "
            "Попробуйте обновить страницу немного позже."
        )
        return

    now = datetime.now(timezone.utc)
    updated_at = parse_time(metadata["updated_at"])
    local_updated = updated_at.astimezone(LOCAL_TZ)

    st.caption(
        "Данные обновлены: "
        f"{local_updated:%d.%m.%Y в %H:%M} "
        "(Новосибирск, UTC+7). "
        "Плановое обновление — раз в 6 часов."
    )

    if now - updated_at > timedelta(hours=8):
        st.warning(
            "Данные не обновлялись более 8 часов. "
            "Прогнозы могут быть устаревшими."
        )

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
            "В загруженном расписании нет матчей "
            "на ближайшие 48 часов. "
            "Расписание появится после очередного обновления."
        )
    else:
        current_day = None

        for forecast in upcoming:
            local_start = parse_time(
                forecast["starts_at"]
            ).astimezone(LOCAL_TZ)

            if local_start.date() != current_day:
                current_day = local_start.date()
                st.subheader(local_start.strftime("%d.%m.%Y"))

            home_percent = round(
                forecast["home_probability"] * 100,
                1,
            )
            away_percent = round(100 - home_percent, 1)

            with st.container(border=True):
                st.caption(
                    f"{local_start:%H:%M} · Новосибирск"
                )

                left, right = st.columns(2)

                with left:
                    st.markdown("**Хозяева**")
                    st.write(forecast["home_name"])
                    st.metric(
                        "Вероятность победы",
                        f"{home_percent:.1f}%",
                    )

                with right:
                    st.markdown("**Гости**")
                    st.write(forecast["away_name"])
                    st.metric(
                        "Вероятность победы",
                        f"{away_percent:.1f}%",
                    )

    st.divider()

    st.caption(
        "Экспериментальная модель Elo с поправкой "
        "на домашнюю площадку. Травмы, составы и отдых "
        "не учитываются. Проценты не являются гарантией "
        "результата и пока не прошли проверку калибровки. "
        "Источник данных: ESPN."
    )


if __name__ == "__main__":
    main()
