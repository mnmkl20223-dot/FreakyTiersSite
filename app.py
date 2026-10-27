import os, hmac, json, sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, abort

app = Flask(__name__)
DB_PATH = os.getenv("DATABASE_PATH", "freaky_tiers.db")
SECRET = os.getenv("SITE_SYNC_SECRET", "")

def connect():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS rankings (id INTEGER PRIMARY KEY CHECK(id=1), ranks TEXT NOT NULL, teams TEXT NOT NULL, updated TEXT NOT NULL)")
        c.execute("INSERT OR IGNORE INTO rankings VALUES (1, '{}', '{}', ?)", (datetime.now(timezone.utc).isoformat(),))
init_db()

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/ranks")
def ranks():
    with connect() as c:
        r = c.execute("SELECT ranks, teams, updated FROM rankings WHERE id=1").fetchone()
    return jsonify({"ranks": json.loads(r["ranks"]), "teams": json.loads(r["teams"]), "updated_at": r["updated"]})

@app.post("/api/sync")
def sync():
    if not SECRET:
        abort(503, description="SITE_SYNC_SECRET is not configured")
    if not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + SECRET):
        abort(401)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("ranks"), dict) or not isinstance(data.get("teams"), dict):
        return jsonify({"error": "Expected ranks and teams objects"}), 400
    now = datetime.now(timezone.utc).isoformat()
    with connect() as c:
        c.execute("UPDATE rankings SET ranks=?, teams=?, updated=? WHERE id=1",
                  (json.dumps(data["ranks"]), json.dumps(data["teams"]), now))
    return jsonify({"ok": True, "updated_at": now})

@app.get("/health")
def health():
    return jsonify({"ok": True})
