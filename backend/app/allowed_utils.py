# backend/app/allowed_utils.py
import json
import os
from typing import Iterable

DEFAULT_JSON = os.path.join(os.path.dirname(__file__), "allowed_emails.json")

def normalize_email(e: str) -> str:
    if not e:
        return ""
    return e.strip().lower()

def load_emails_from_json(path: str | None = None) -> list[str]:
    path = path or DEFAULT_JSON
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            emails = data.get("allowed_emails", [])
        elif isinstance(data, list):
            emails = data
        else:
            return []
        return [normalize_email(x) for x in emails if isinstance(x, str) and x.strip()]
    except FileNotFoundError:
        return []
    except Exception:
        # any parsing error -> behave as empty list
        return []

def email_in_list(email: str, allowed_iter: Iterable[str]) -> bool:
    en = normalize_email(email)
    return any(en == normalize_email(a) for a in allowed_iter)
