from flask import Flask, render_template, jsonify, request
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH   = os.path.join(ROOT, "config.json")
WARNINGS_PATH = os.path.join(ROOT, "warnings.json")

app = Flask(__name__)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

def load_warnings():
    if not os.path.exists(WARNINGS_PATH):
        return {}
    with open(WARNINGS_PATH) as f:
        return json.load(f)

def save_warnings(data):
    with open(WARNINGS_PATH, "w") as f:
        json.dump(data, f, indent=4)

# ---- PAGES ----

@app.route("/")
def index():
    return render_template("index.html")

# ---- CONFIG API ----

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())

@app.route("/api/config", methods=["POST"])
def update_config():
    updates = request.get_json()
    if not updates:
        return jsonify({"error": "No data"}), 400

    cfg = load_config()

    allowed = {
        "prefix", "log_channel_id",
        "skullboard_channel_id", "skullboard_threshold",
        "ticket_support_role_id", "ticket_category_id",
        "warn_role_1", "warn_role_2", "warn_role_3",
        "authorized_role_id",
    }

    for key, value in updates.items():
        if key not in allowed:
            continue
        # Convert numeric strings to int or null
        if value == "" or value is None:
            cfg[key] = None
        else:
            try:
                cfg[key] = int(value)
            except (ValueError, TypeError):
                cfg[key] = value

    save_config(cfg)
    return jsonify({"ok": True, "config": cfg})

# ---- STATS API ----

@app.route("/api/stats")
def stats():
    cfg = load_config()
    warnings = load_warnings()
    active = {uid: w for uid, w in warnings.items() if w}
    return jsonify({
        "total_warnings": sum(len(v) for v in warnings.values()),
        "warned_users":   len(active),
        "tickets":        cfg.get("ticket_count", 0),
        "skullboard_threshold": cfg.get("skullboard_threshold", 3),
    })

# ---- WARNINGS API ----

@app.route("/api/warnings")
def get_warnings():
    warnings = load_warnings()
    result = []
    for uid, entries in warnings.items():
        if entries:
            result.append({"user_id": uid, "warnings": entries})
    return jsonify(result)

@app.route("/api/warnings/<user_id>/clear", methods=["POST"])
def clear_user_warnings(user_id):
    data = load_warnings()
    data[user_id] = []
    save_warnings(data)
    return jsonify({"ok": True})

@app.route("/api/warnings/<user_id>/<int:index>", methods=["DELETE"])
def delete_warning(user_id, index):
    data = load_warnings()
    if user_id not in data or index >= len(data[user_id]):
        return jsonify({"error": "Not found"}), 404
    data[user_id].pop(index)
    save_warnings(data)
    return jsonify({"ok": True})

def run():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
