import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from config.json or return defaults."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"prefix": "!"}

def save_config(config):
    """Save configuration to config.json."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
