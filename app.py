import altair as alt
import streamlit as st

from api_client import login
from gemini_client import GeminiError, chat_reply
from weather_client import (
    WeatherError,
    forecast_dataframe,
    geocode,
    get_current_weather,
    get_forecast,
    openweather_api_key,
    today_summary,
    weather_context,
)

st.set_page_config(page_title="AI Weather Dashboard", page_icon="⛈", layout="centered")

if "token" not in st.session_state:
    st.session_state["token"] = None
    st.session_state["username"] = None
if "units" not in st.session_state:
    st.session_state["units"] = "imperial"
if "location" not in st.session_state:
    st.session_state["location"] = None
if "matches" not in st.session_state:
    st.session_state["matches"] = []
if "search_query" not in st.session_state:
    st.session_state["search_query"] = "Austin"
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = None
if "default_loaded" not in st.session_state:
    st.session_state["default_loaded"] = False


def reset_chat_if_scope_changed(location_label, units):
    scope = (location_label, units)
    if st.session_state.get("chat_scope") != scope:
        st.session_state["messages"] = []
        st.session_state["chat_scope"] = scope


def apply_search(query: str) -> None:
    try:
        api_key = openweather_api_key()
        matches = geocode(query, api_key)
    except WeatherError as exc:
        st.session_state["matches"] = []
        st.session_state["location"] = None
        st.error(str(exc))
        return
    if not matches:
        st.session_state["matches"] = []
        st.session_state["location"] = None
        st.warning("No matching locations. Try a city name like London or Austin,TX,US.")
        return
    st.session_state["matches"] = matches
    st.session_state["location"] = matches[0]


if st.session_state["token"] is None:
    st.title("Login to AI Weather Dashboard")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            token = login(username, password)
            if token:
                st.session_state["token"] = token
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid credentials")
else:
    with st.sidebar:
        st.write(f"Logged in as **{st.session_state['username']}**")
        st.radio(
            "Units",
            options=["imperial", "metric"],
            format_func=lambda value: "°F / mph (imperial)" if value == "imperial" else "°C / m/s (metric)",
            key="units",
        )
        if st.button("Logout"):
            st.session_state["token"] = None
            st.session_state["username"] = None
            st.rerun()

    st.title("AI Weather Dashboard")
    st.caption("Current conditions, a 5-day forecast, and outfit advice grounded in the weather.")

    if not st.session_state["default_loaded"] and st.session_state["location"] is None:
        st.session_state["default_loaded"] = True
        apply_search(st.session_state["search_query"])

    with st.form("location_search"):
        st.text_input(
            "Location search",
            key="search_query",
            placeholder="City name, e.g. Austin,TX,US",
        )
        searched = st.form_submit_button("Search")
        if searched:
            apply_search(st.session_state["search_query"])

    matches = st.session_state["matches"]
    if len(matches) > 1:
        labels = [place["label"] for place in matches]
        current_label = (st.session_state["location"] or {}).get("label")
        index = labels.index(current_label) if current_label in labels else 0
        selected_label = st.selectbox("Matching locations", labels, index=index)
        st.session_state["location"] = next(
            place for place in matches if place["label"] == selected_label
        )

    location = st.session_state["location"]
    reset_chat_if_scope_changed(location["label"] if location else None, st.session_state["units"])

    current = None
    forecast = []
    today = {}
    context = ""

    if location:
        try:
            api_key = openweather_api_key()
            current = get_current_weather(
                location["lat"], location["lon"], st.session_state["units"], api_key
            )
            forecast = get_forecast(
                location["lat"], location["lon"], st.session_state["units"], api_key
            )
            today = today_summary(forecast)
            context = weather_context(location["label"], current, today)
        except WeatherError as exc:
            st.error(str(exc))
            current = None

    if current:
        temp_u = "°F" if st.session_state["units"] == "imperial" else "°C"
        wind_u = "mph" if st.session_state["units"] == "imperial" else "m/s"
        heading_cols = st.columns([1, 5])
        with heading_cols[0]:
            if current.get("icon_url"):
                st.image(current["icon_url"], width=80)
        with heading_cols[1]:
            st.subheader(location["label"])
            st.write(current["description"].title() if current.get("description") else "")

        def fmt(value, suffix, digits=0):
            if value is None:
                return "—"
            return f"{value:.{digits}f}{suffix}"

        metric_cols = st.columns(4)
        metric_cols[0].metric("Temperature", fmt(current.get("temp"), temp_u))
        metric_cols[1].metric("Feels like", fmt(current.get("feels_like"), temp_u))
        metric_cols[2].metric("Humidity", fmt(current.get("humidity"), "%"))
        metric_cols[3].metric("Wind", fmt(current.get("wind_speed"), f" {wind_u}", digits=1))

        df = forecast_dataframe(forecast)
        if not df.empty:
            st.subheader("5-day forecast")
            y_title = f"Temperature ({temp_u})"
            chart = (
                alt.Chart(df)
                .mark_line(point=True)
                .encode(
                    x=alt.X("datetime:T", title="Date / time"),
                    y=alt.Y("temp:Q", title=y_title),
                    tooltip=["datetime:T", alt.Tooltip("temp:Q", title=y_title), "description:N"],
                )
                .properties(height=320)
            )
            st.altair_chart(chart, width='stretch')
        else:
            st.info("Forecast data is not available for this location.")
    elif not location:
        st.info("Search for a city to load weather.")

    st.divider()
    st.subheader("What should I wear today?")
    weather_ready = bool(current and context)
    if not weather_ready:
        st.warning("Load a location first so outfit advice can use the current weather.")
    else:
        chip_cols = st.columns(3)
        suggestions = [
            "What should I wear today?",
            "Do I need an umbrella?",
            "Is it good for a run?",
        ]
        for column, suggestion in zip(chip_cols, suggestions):
            if column.button(suggestion, width='stretch'):
                st.session_state["pending_prompt"] = suggestion
                st.rerun()

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "What should I wear today?",
        disabled=not weather_ready,
    )
    if st.session_state["pending_prompt"] and weather_ready:
        prompt = st.session_state["pending_prompt"]
        st.session_state["pending_prompt"] = None

    if prompt and weather_ready:
        history = list(st.session_state["messages"])
        st.session_state["messages"].append({"role": "user", "content": prompt})
        try:
            with st.spinner("Asking Gemini…"):
                reply = chat_reply(prompt, context, history)
        except GeminiError as exc:
            reply = str(exc)
        st.session_state["messages"].append({"role": "assistant", "content": reply})
        st.rerun()
