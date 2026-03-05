"""Configuration management for addlib rules (load, save, validation)."""

import json
import os
import uuid
from pathlib import Path

RULES_FILE = "rules.json"
VALID_TYPES = ("movie", "tv_series")


def get_rules_path() -> str:
    """Return the path to rules.json (in script directory)."""
    return str(Path(__file__).parent / RULES_FILE)


def load_rules(rules_path: str | None = None) -> list[dict]:
    """Load rules from JSON file. Returns empty list if file missing or invalid."""
    path = rules_path or get_rules_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("rules", [])
    except (json.JSONDecodeError, IOError):
        return []


def save_rules(rules: list[dict], rules_path: str | None = None) -> None:
    """Save rules to JSON file."""
    path = rules_path or get_rules_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"rules": rules}, f, indent=2, ensure_ascii=False)


def validate_rule(rule: dict) -> tuple[bool, str]:
    """
    Validate a rule. Returns (ok, error_message).
    """
    required = ("name", "source", "target", "type")
    for key in required:
        if key not in rule or not str(rule[key]).strip():
            return False, f"Missing or empty required field: {key}"

    ct = str(rule["type"]).strip().lower()
    if ct not in VALID_TYPES:
        return False, f"Invalid type '{rule['type']}'. Must be 'movie' or 'tv_series'."

    source = str(rule["source"]).strip()
    target = str(rule["target"]).strip()

    if not os.path.isdir(source):
        return False, f"Source is not a valid directory: {source}"
    if not os.path.isdir(target):
        return False, f"Target is not a valid directory: {target}"

    return True, ""


def new_rule(
    name: str,
    source: str,
    target: str,
    content_type: str,
    organize_by_initial: bool = False,
) -> dict:
    """Create a new rule dict with generated id."""
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "source": source.strip(),
        "target": target.strip(),
        "type": content_type.strip().lower(),
        "organize_by_initial": bool(organize_by_initial),
    }
