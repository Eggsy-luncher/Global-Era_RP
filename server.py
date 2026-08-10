#!/usr/bin/env python3
"""
Global Era RP — Zero-dependency Backend
Works with pure Python (no pip install needed).
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
import json
import os
import uuid

PORT = 5000
DATA_DIR = "data"
ADMIN_PASSWORD = "globalera2026"   # change this later

os.makedirs(DATA_DIR, exist_ok=True)

REDEEM_FILE = os.path.join(DATA_DIR, "redeem_codes.json")
REWARDS_FILE = os.path.join(DATA_DIR, "daily_rewards.json")
NEWS_FILE = os.path.join(DATA_DIR, "news.json")
CLAIMS_FILE = os.path.join(DATA_DIR, "claims.json")


def load_json(path, default):
    if not os.path.exists(path):
        save_json(path, default)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def init_data():
    if not os.path.exists(REDEEM_FILE):
        save_json(REDEEM_FILE, [
            {"code": "WELCOME100", "reward": "100 State Coins", "max_uses": 1000, "used": 0, "active": True},
            {"code": "LAUNCH50", "reward": "50 State Coins + Starter Pack", "max_uses": 500, "used": 0, "active": True},
        ])
    if not os.path.exists(NEWS_FILE):
        save_json(NEWS_FILE, [
            {
                "id": "1",
                "title": "Game Launch Announcement",
                "slug": "news-launch",
                "summary": "Track the expected release timeline, server details, and the first public update.",
                "date": "2026-08-01",
                "category": "Coming Soon"
            },
            {
                "id": "2",
                "title": "Community Preparations",
                "slug": "news-community",
                "summary": "See what content is being prepared for new players.",
                "date": "2026-08-05",
                "category": "New"
            },
            {
                "id": "3",
                "title": "What to Expect",
                "slug": "news-expectations",
                "summary": "Learn what features and gameplay systems are being highlighted.",
                "date": "2026-08-08",
                "category": "Info"
            },
        ])
    if not os.path.exists(REWARDS_FILE):
        save_json(REWARDS_FILE, {
            "rewards": [
                {"day": 1, "reward": "50 State Coins"},
                {"day": 2, "reward": "100 State Coins"},
                {"day": 3, "reward": "Starter Pack"},
                {"day": 4, "reward": "150 State Coins"},
                {"day": 5, "reward": "Random Case"},
                {"day": 6, "reward": "200 State Coins"},
                {"day": 7, "reward": "Premium Bundle"},
            ],
            "cooldown_hours": 20
        })
    if not os.path.exists(CLAIMS_FILE):
        save_json(CLAIMS_FILE, {})


init_data()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Password")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            return self.json_response({
                "status": "ok",
                "server": "Global Era RP Backend",
                "time": datetime.utcnow().isoformat()
            })

        if path == "/api/news":
            return self.json_response(load_json(NEWS_FILE, []))

        if path == "/api/rewards":
            return self.json_response(load_json(REWARDS_FILE, {}))

        if path == "/api/rewards/status":
            return self.handle_rewards_status()

        if path == "/api/codes":
            return self.handle_list_codes()

        if path == "/admin":
            return self.serve_admin()

        if path == "/" or path == "":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_body()

        if path == "/api/redeem":
            return self.handle_redeem(body)

        if path == "/api/rewards/claim":
            return self.handle_claim()

        if path == "/api/codes":
            return self.handle_create_code(body)

        if path == "/api/news":
            return self.handle_add_news(body)

        self.send_error(404, "Not Found")

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def get_client_ip(self):
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def check_admin(self):
        return (self.headers.get("X-Admin-Password") or "") == ADMIN_PASSWORD

    def handle_redeem(self, data):
        code = (data.get("code") or "").strip().upper()
        if not code:
            return self.json_response({"success": False, "message": "Please enter a code."}, 400)

        codes = load_json(REDEEM_FILE, [])
        found = next((c for c in codes if c["code"].upper() == code), None)

        if not found:
            return self.json_response({"success": False, "message": "Invalid code."}, 404)
        if not found.get("active", True):
            return self.json_response({"success": False, "message": "This code is no longer active."}, 400)
        if found["used"] >= found["max_uses"]:
            return self.json_response({"success": False, "message": "This code has reached its maximum uses."}, 400)

        found["used"] += 1
        save_json(REDEEM_FILE, codes)
        return self.json_response({
            "success": True,
            "message": f"Success! You received: {found['reward']}",
            "reward": found["reward"]
        })

    def handle_rewards_status(self):
        ip = self.get_client_ip()
        claims = load_json(CLAIMS_FILE, {})
        config = load_json(REWARDS_FILE, {})
        player = claims.get(ip, {"last_claim": None, "streak": 0, "total_claims": 0})

        can_claim = True
        remaining = 0
        if player.get("last_claim"):
            last = datetime.fromisoformat(player["last_claim"])
            hours = (datetime.utcnow() - last).total_seconds() / 3600
            cooldown = config.get("cooldown_hours", 20)
            if hours < cooldown:
                can_claim = False
                remaining = round(cooldown - hours, 1)

        return self.json_response({
            "can_claim": can_claim,
            "streak": player.get("streak", 0),
            "total_claims": player.get("total_claims", 0),
            "next_claim_in_hours": remaining
        })

    def handle_claim(self):
        ip = self.get_client_ip()
        claims = load_json(CLAIMS_FILE, {})
        config = load_json(REWARDS_FILE, {})
        cooldown = config.get("cooldown_hours", 20)
        now = datetime.utcnow()
        player = claims.get(ip, {"last_claim": None, "streak": 0, "total_claims": 0})

        if player.get("last_claim"):
            last = datetime.fromisoformat(player["last_claim"])
            hours = (now - last).total_seconds() / 3600
            if hours < cooldown:
                remaining = round(cooldown - hours, 1)
                return self.json_response({
                    "success": False,
                    "message": f"You can claim again in {remaining} hours.",
                    "next_claim_in_hours": remaining
                }, 429)

        if player.get("last_claim"):
            last = datetime.fromisoformat(player["last_claim"])
            if (now - last).total_seconds() / 3600 < 48:
                player["streak"] = player.get("streak", 0) + 1
            else:
                player["streak"] = 1
        else:
            player["streak"] = 1

        player["total_claims"] = player.get("total_claims", 0) + 1
        player["last_claim"] = now.isoformat()

        day = ((player["streak"] - 1) % 7) + 1
        rewards_list = config.get("rewards", [])
        reward_item = next((r for r in rewards_list if r["day"] == day), {"reward": "50 State Coins"})

        claims[ip] = player
        save_json(CLAIMS_FILE, claims)

        return self.json_response({
            "success": True,
            "message": f"Day {day} reward claimed!",
            "reward": reward_item["reward"],
            "streak": player["streak"],
            "total_claims": player["total_claims"]
        })

    def handle_list_codes(self):
        if not self.check_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        return self.json_response(load_json(REDEEM_FILE, []))

    def handle_create_code(self, data):
        if not self.check_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        code = (data.get("code") or "").strip().upper()
        if not code:
            return self.json_response({"error": "Code is required"}, 400)
        codes = load_json(REDEEM_FILE, [])
        new_code = {
            "code": code,
            "reward": data.get("reward", "Unknown reward"),
            "max_uses": int(data.get("max_uses", 100)),
            "used": 0,
            "active": True
        }
        codes.append(new_code)
        save_json(REDEEM_FILE, codes)
        return self.json_response(new_code, 201)

    def handle_add_news(self, data):
        if not self.check_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        news = load_json(NEWS_FILE, [])
        item = {
            "id": str(uuid.uuid4())[:8],
            "title": data.get("title", "Untitled"),
            "slug": data.get("slug", "news-" + str(uuid.uuid4())[:6]),
            "summary": data.get("summary", ""),
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "category": data.get("category", "Update")
        }
        news.insert(0, item)
        save_json(NEWS_FILE, news)
        return self.json_response(item, 201)

    def serve_admin(self):
        html = """<!DOCTYPE html>
<html>
<head>
  <title>Global Era RP — Admin</title>
  <style>
    body{font-family:Arial;background:#0d1117;color:#e6edf3;padding:40px;max-width:800px;margin:auto}
    h1{color:#f5cf22}
    input,button{padding:10px;margin:6px 0;width:100%;box-sizing:border-box;
    border-radius:6px;border:1px solid #30363d;background:#161b22;color:#fff}
    button{background:#f5cf22;color:#000;font-weight:bold;cursor:pointer}
    .card{background:#161b22;padding:20px;border-radius:8px;margin-bottom:20px;border:1px solid #30363d}
    pre{background:#0d1117;padding:12px;overflow:auto}
  </style>
</head>
<body>
  <h1>GLOBAL ERA RP — Admin</h1>
  <p>Password: <code>globalera2026</code></p>
  <div class="card">
    <h3>Create Redeem Code</h3>
    <input id="code" placeholder="CODE">
    <input id="reward" placeholder="Reward description">
    <input id="max" type="number" value="100">
    <button onclick="createCode()">Create</button>
    <pre id="out"></pre>
  </div>
  <div class="card">
    <h3>List Codes</h3>
    <button onclick="listCodes()">Refresh</button>
    <pre id="list"></pre>
  </div>
  <script>
    const pwd = prompt("Admin password:") || "";
    async function createCode(){
      const r = await fetch("/api/codes",{method:"POST",
        headers:{"Content-Type":"application/json","X-Admin-Password":pwd},
        body:JSON.stringify({code:code.value,reward:reward.value,max_uses:max.value})});
      out.textContent = JSON.stringify(await r.json(),null,2);
    }
    async function listCodes(){
      const r = await fetch("/api/codes",{headers:{"X-Admin-Password":pwd}});
      list.textContent = JSON.stringify(await r.json(),null,2);
    }
  </script>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    print("=" * 50)
    print("  GLOBAL ERA RP — Backend")
    print("=" * 50)
    print(f"  Website : http://127.0.0.1:{PORT}")
    print(f"  Admin   : http://127.0.0.1:{PORT}/admin")
    print(f"  Password: {ADMIN_PASSWORD}")
    print("=" * 50)
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()