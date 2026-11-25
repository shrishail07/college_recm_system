import os
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "colleges_sample.csv"


def get_groq_api_key() -> str:
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        raise ValueError("GROQ_API_KEY is missing. Add it to Streamlit Secrets or environment variables.")
    return key


def get_groq_model() -> str:
    if "GROQ_MODEL" in st.secrets:
        return st.secrets["GROQ_MODEL"]
    return os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
