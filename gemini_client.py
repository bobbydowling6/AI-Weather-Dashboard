from __future__ import annotations

import streamlit as st
from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """You are a clothing advisor for a weather dashboard.
Use only the provided weather data to give specific outfit advice.
Mention layers, footwear, rain gear, and sun protection when they matter.
If weather data is missing, ask the user to search for a location first.
Keep answers concise and practical.
"""

# gemini-2.5-flash is closed to new API keys; 3.5 Flash works with this project's key.
MODEL = "gemini-3.5-flash"


class GeminiError(Exception):
    """Raised when Gemini cannot fulfill a request."""


def _redact(message: str, secret: str) -> str:
    if secret:
        message = message.replace(secret, "[redacted]")
    return message


def gemini_api_key() -> str:
    """Read GEMINI_API_KEY from top-level secrets, then a nested TOML fallback."""
    key = None
    try:
        key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        key = None
    if not key:
        try:
            key = st.secrets["database"]["users"]["GEMINI_API_KEY"]
        except Exception:
            key = None
    if not key:
        raise GeminiError(
            "Gemini API key was not found. Put GEMINI_API_KEY at the top of "
            ".streamlit/secrets.toml, above any [database.users] section, then restart Streamlit."
        )
    return str(key)


def chat_reply(user_message: str, weather_context: str, history: list[dict]) -> str:
    api_key = gemini_api_key()
    client = genai.Client(api_key=api_key)
    system = SYSTEM_INSTRUCTION + "\n\nCurrent weather data:\n" + (
        weather_context or "No weather loaded."
    )
    contents: list[types.Content] = []
    for message in history:
        role = "user" if message.get("role") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=message.get("content") or "")])
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system),
        )
    except Exception as exc:
        detail = _redact(str(exc), api_key)
        raise GeminiError(f"Gemini request failed: {detail}") from exc
    text = (getattr(response, "text", None) or "").strip()
    if not text:
        return "I could not generate outfit advice. Try again in a moment."
    return text
