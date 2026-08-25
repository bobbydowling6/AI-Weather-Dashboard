# AI Weather Dashboard

Streamlit app that shows current weather, a 5-day forecast chart, and location search via OpenWeather. A Gemini chat under the dashboard answers questions like “What should I wear today?” using the loaded weather.

## Setup

1. Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Add keys in `.streamlit/secrets.toml` (this file is gitignored):

```toml
OpenWeatherAPIKey = "your-openweather-key"
GEMINI_API_KEY = "your-gemini-key"

[database.users]
admin = "your-password"
```

Get an OpenWeather key from [OpenWeather](https://openweathermap.org/api) and a Gemini key from [Google AI Studio](https://aistudio.google.com/apikey). Do not commit secrets.

## Run

You need two processes from the project root:

1. Auth API:

```bash
uvicorn backend:app --reload --port 8000
```

2. Dashboard:

```bash
streamlit run app.py
```

Log in with a username and password from `[database.users]` in secrets (default example: `admin`).

## Features

- Search a city (for example `London` or `Austin,TX,US`) and pick among matches.
- Current temperature, feels-like, humidity, and wind.
- 5-day / 3-hour temperature chart.
- Imperial or metric units in the sidebar.
- Outfit chat grounded in the currently displayed weather.
