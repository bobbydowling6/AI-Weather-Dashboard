from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


class WeatherError(Exception):
    """Raised when OpenWeather cannot fulfill a request."""


def openweather_api_key() -> str:
    try:
        key = st.secrets["OpenWeatherAPIKey"]
    except Exception as exc:
        raise WeatherError(
            "OpenWeather API key is missing. Add OpenWeatherAPIKey to .streamlit/secrets.toml."
        ) from exc
    if not key:
        raise WeatherError(
            "OpenWeather API key is empty. Add OpenWeatherAPIKey to .streamlit/secrets.toml."
        )
    return str(key)


def _raise_for_status(response: requests.Response) -> None:
    if response.status_code == 401:
        raise WeatherError(
            "OpenWeather rejected the API key. Check OpenWeatherAPIKey in secrets.toml."
        )
    if response.status_code == 404:
        raise WeatherError("Location was not found. Try a different city name.")
    if response.status_code == 429:
        raise WeatherError("OpenWeather rate limit reached. Wait a minute and try again.")
    if response.status_code >= 400:
        raise WeatherError(f"OpenWeather request failed ({response.status_code}).")


def location_label(place: dict) -> str:
    parts = [place.get("name") or "Unknown"]
    if place.get("state"):
        parts.append(place["state"])
    if place.get("country"):
        parts.append(place["country"])
    return ", ".join(parts)


@st.cache_data(ttl=600)
def geocode(query: str, _api_key: str, limit: int = 5) -> list[dict]:
    if not query or not query.strip():
        return []
    try:
        response = requests.get(
            GEOCODE_URL,
            params={"q": query.strip(), "limit": limit, "appid": _api_key},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise WeatherError("Could not reach OpenWeather. Check your network connection.") from exc
    _raise_for_status(response)
    data = response.json()
    if not isinstance(data, list):
        raise WeatherError("Unexpected geocoding response from OpenWeather.")
    results = []
    for item in data:
        results.append(
            {
                "name": item.get("name"),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "country": item.get("country"),
                "state": item.get("state"),
                "label": location_label(item),
            }
        )
    return results


@st.cache_data(ttl=600)
def get_current_weather(lat: float, lon: float, units: str, _api_key: str) -> dict:
    try:
        response = requests.get(
            CURRENT_URL,
            params={"lat": lat, "lon": lon, "appid": _api_key, "units": units},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise WeatherError("Could not reach OpenWeather. Check your network connection.") from exc
    _raise_for_status(response)
    data = response.json()
    weather0 = (data.get("weather") or [{}])[0]
    main = data.get("main") or {}
    wind = data.get("wind") or {}
    sys = data.get("sys") or {}
    icon = weather0.get("icon")
    return {
        "name": data.get("name"),
        "country": sys.get("country"),
        "temp": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "description": weather0.get("description") or "",
        "icon": icon,
        "icon_url": f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else None,
        "units": units,
    }


@st.cache_data(ttl=600)
def get_forecast(lat: float, lon: float, units: str, _api_key: str) -> list[dict]:
    try:
        response = requests.get(
            FORECAST_URL,
            params={"lat": lat, "lon": lon, "appid": _api_key, "units": units},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise WeatherError("Could not reach OpenWeather. Check your network connection.") from exc
    _raise_for_status(response)
    data = response.json()
    items = data.get("list") or []
    rows = []
    for item in items:
        main = item.get("main") or {}
        weather0 = (item.get("weather") or [{}])[0]
        rows.append(
            {
                "dt_txt": item.get("dt_txt"),
                "temp": main.get("temp"),
                "temp_min": main.get("temp_min"),
                "temp_max": main.get("temp_max"),
                "humidity": main.get("humidity"),
                "description": weather0.get("description") or "",
                "pop": item.get("pop") or 0,
                "rain_3h": (item.get("rain") or {}).get("3h") or 0,
                "snow_3h": (item.get("snow") or {}).get("3h") or 0,
            }
        )
    return rows


def forecast_dataframe(forecast: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(forecast)
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["dt_txt"])
    return df


def today_summary(forecast: list[dict]) -> dict:
    if not forecast:
        return {}
    first_date = (forecast[0].get("dt_txt") or "")[:10]
    if not first_date:
        return {}
    today_rows = [row for row in forecast if (row.get("dt_txt") or "").startswith(first_date)]
    temps = [row["temp"] for row in today_rows if row.get("temp") is not None]
    rain = any((row.get("rain_3h") or 0) > 0 or (row.get("pop") or 0) >= 0.4 for row in today_rows)
    snow = any((row.get("snow_3h") or 0) > 0 for row in today_rows)
    return {
        "date": first_date,
        "high": max(temps) if temps else None,
        "low": min(temps) if temps else None,
        "rain_likely": rain,
        "snow_likely": snow,
    }


def weather_context(label: str, current: dict, today: dict) -> str:
    temp_u = "°F" if current.get("units") == "imperial" else "°C"
    wind_u = "mph" if current.get("units") == "imperial" else "m/s"
    lines = [
        f"Location: {label}",
        f"Current temperature: {current.get('temp')}{temp_u}",
        f"Feels like: {current.get('feels_like')}{temp_u}",
        f"Humidity: {current.get('humidity')}%",
        f"Wind: {current.get('wind_speed')} {wind_u}",
        f"Conditions: {current.get('description')}",
    ]
    if today:
        lines.append(
            f"Today's high/low: {today.get('high')}{temp_u} / {today.get('low')}{temp_u}"
        )
        if today.get("rain_likely"):
            lines.append("Rain is likely today.")
        if today.get("snow_likely"):
            lines.append("Snow is likely today.")
    return "\n".join(lines)
