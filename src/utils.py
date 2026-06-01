from __future__ import annotations
import os
import re
from pathlib import Path
from typing import Any, Dict
import yaml

def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def normalize_text(text: str) -> str:
    text = text or ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9%\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def app_password() -> str | None:
    return os.environ.get("APP_PASSWORD")

def password_gate(st, password: str | None) -> bool:
    if not password:
        st.info("No APP_PASSWORD is configured. The app is currently open.")
        return True
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    entered = st.text_input("Enter app password", type="password")
    if entered == password:
        st.session_state.authenticated = True
        st.rerun()
    elif entered:
        st.error("Incorrect password.")
    return False

def score_to_band(score: float) -> str:
    if score >= 85:
        return "Outstanding"
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Mixed"
    return "Weak"

def recommendation_from_score(score: float) -> str:
    if score >= 85:
        return "Strongly advance"
    if score >= 70:
        return "Advance"
    if score >= 55:
        return "Discuss / borderline"
    return "Do not advance"
