import json
import os

WARNINGS_FILE = "warnings.json"

def load_warnings() -> dict:
    if not os.path.exists(WARNINGS_FILE):
        return {}
    with open(WARNINGS_FILE, "r") as f:
        return json.load(f)

def save_warnings(data: dict):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_warning(user_id: int, reason: str, moderator: str) -> int:
    data = load_warnings()
    key = str(user_id)
    if key not in data:
        data[key] = []
    data[key].append({"reason": reason, "moderator": moderator})
    save_warnings(data)
    return len(data[key])

def get_warnings(user_id: int) -> list:
    return load_warnings().get(str(user_id), [])

def clear_warnings(user_id: int):
    data = load_warnings()
    data[str(user_id)] = []
    save_warnings(data)
