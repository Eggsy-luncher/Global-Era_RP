#!/usr/bin/env python3
"""
Global Era RP — Zero-dependency Backend
Uses only Python standard library (no Flask, no pip needed).
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
import json
import os
import uuid

PORT = int(os.environ.get("PORT", 5000))
DATA_DIR = "data"
ADMIN_PASSWORD = "globalera2026"

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
            {"id": "1", "title": "Game Launch Announcement", "slug": "news-launch",
             "summary": "Track the expected release timeline, server details, and the first public update.",
             "body": "", "date": "2026-08-01", "category": "Coming Soon"},
            {"id": "2", "title": "Community Preparations", "slug": "news-community",
             "summary": "See what content is being prepared for new players.",
             "body": "", "date": "2026-08-05", "category": "New"},
            {"id": "3", "title": "What to Expect", "slug": "news-expectations",
             "summary": "Learn what features and gameplay systems are being highlighted.",
             "body": "", "date": "2026-08-08", "category": "Info"},
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

        if path == "/api/news/delete":
            return self.handle_delete_news(body)

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
        title = (data.get("title") or "Untitled").strip()
        slug_base = "".join(c if c.isalnum() or c in "- " else "" for c in title.lower()).strip().replace(" ", "-")[:40]
        item = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "slug": data.get("slug") or ("news-" + slug_base or str(uuid.uuid4())[:6]),
            "summary": (data.get("summary") or "").strip(),
            "body": (data.get("body") or data.get("content") or "").strip(),
            "date": data.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "category": (data.get("category") or "Update").strip()
        }
        news.insert(0, item)
        save_json(NEWS_FILE, news)
        return self.json_response(item, 201)

    def handle_delete_news(self, data):
        if not self.check_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        news_id = (data.get("id") or "").strip()
        if not news_id:
            return self.json_response({"error": "id required"}, 400)
        news = load_json(NEWS_FILE, [])
        new_list = [n for n in news if n.get("id") != news_id]
        if len(new_list) == len(news):
            return self.json_response({"error": "News not found"}, 404)
        save_json(NEWS_FILE, new_list)
        return self.json_response({"success": True, "deleted": news_id})

    def serve_admin(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Global Era RP — Admin</title>
  <style>
    *{box-sizing:border-box}
    body{font-family:Arial,Helvetica,sans-serif;background:#0d1117;color:#e6edf3;padding:24px;max-width:920px;margin:auto}
    h1{color:#f5cf22;margin:0 0 6px}
    h2{color:#f5cf22;font-size:18px;margin:0 0 14px}
    p.sub{color:#8b949e;margin:0 0 24px;font-size:13px}
    .card{background:#161b22;padding:20px;border-radius:10px;margin-bottom:18px;border:1px solid #30363d}
    input,textarea,select,button{
      padding:11px 12px;margin:6px 0;width:100%;box-sizing:border-box;
      border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#fff;font-size:14px
    }
    textarea{min-height:110px;resize:vertical;font-family:inherit}
    button{background:#f5cf22;color:#000;font-weight:bold;cursor:pointer;border:none}
    button.secondary{background:#21262d;color:#e6edf3;border:1px solid #30363d}
    button.danger{background:#da3633;color:#fff}
    label{display:block;font-size:12px;color:#8b949e;margin-top:8px}
    pre{background:#0d1117;padding:12px;overflow:auto;border-radius:6px;font-size:12px;max-height:220px}
    .row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
    .news-item{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:14px;margin-bottom:10px}
    .news-item h4{margin:0 0 6px;color:#f0f3f5}
    .news-item p{margin:0 0 8px;color:#8b949e;font-size:13px;line-height:1.4}
    .news-meta{font-size:11px;color:#6e7681;margin-bottom:8px}
    .news-actions{display:flex;gap:8px}
    .news-actions button{width:auto;padding:8px 12px;font-size:12px}
    .tabs{display:flex;gap:8px;margin-bottom:18px;flex-wrap:wrap}
    .tab{width:auto;padding:10px 16px;background:#21262d;color:#c9d1d9;border:1px solid #30363d}
    .tab.active{background:#f5cf22;color:#000}
    .panel{display:none}
    .panel.active{display:block}
    .ok{color:#3dd68c}
    .err{color:#ff6b6b}
    @media(max-width:600px){.row{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <h1>GLOBAL ERA RP — Admin</h1>
  <p class="sub">Manage news announcements and redeem codes.</p>

  <div class="tabs">
    <button class="tab active" data-tab="news">News / Announcements</button>
    <button class="tab" data-tab="codes">Redeem Codes</button>
  </div>

  <div class="panel active" id="panel-news">
    <div class="card">
      <h2>Publish News Announcement</h2>
      <label>Title</label>
      <input id="nTitle" placeholder="e.g. Weekend Event Live">
      <div class="row">
        <div>
          <label>Category</label>
          <select id="nCategory">
            <option>Update</option>
            <option>Event</option>
            <option>Announcement</option>
            <option>Coming Soon</option>
            <option>New</option>
            <option>Info</option>
            <option>Patch</option>
          </select>
        </div>
        <div>
          <label>Date (optional)</label>
          <input id="nDate" type="date">
        </div>
      </div>
      <label>Short summary</label>
      <input id="nSummary" placeholder="One or two sentences for the card preview">
      <label>Full body / announcement text</label>
      <textarea id="nBody" placeholder="Write the full announcement..."></textarea>
      <button id="btnPublish">Publish Announcement</button>
      <pre id="nResult"></pre>
    </div>

    <div class="card">
      <h2>Current News Posts</h2>
      <button class="secondary" id="btnRefreshNews" style="width:auto;margin-bottom:12px">Refresh list</button>
      <div id="newsList">Loading...</div>
    </div>
  </div>

  <div class="panel" id="panel-codes">
    <div class="card">
      <h2>Create Redeem Code</h2>
      <label>Code</label>
      <input id="code" placeholder="SUMMER2026">
      <label>Reward description</label>
      <input id="reward" placeholder="100 State Coins">
      <label>Max uses</label>
      <input id="max" type="number" value="100">
      <button id="btnCreateCode">Create Code</button>
      <pre id="codeResult"></pre>
    </div>
    <div class="card">
      <h2>All Codes</h2>
      <button class="secondary" id="btnListCodes" style="width:auto;margin-bottom:12px">Refresh</button>
      <pre id="codesList"></pre>
    </div>
  </div>

  <script>
    let pwd = sessionStorage.getItem("ger_admin_pwd") || "";
    if (!pwd) {
      pwd = prompt("Admin password:") || "";
      if (pwd) sessionStorage.setItem("ger_admin_pwd", pwd);
    }

    const headers = () => ({
      "Content-Type": "application/json",
      "X-Admin-Password": pwd
    });

    document.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
      });
    });

    document.getElementById("btnPublish").addEventListener("click", async () => {
      const title = document.getElementById("nTitle").value.trim();
      const summary = document.getElementById("nSummary").value.trim();
      const body = document.getElementById("nBody").value.trim();
      const category = document.getElementById("nCategory").value;
      const date = document.getElementById("nDate").value;
      const out = document.getElementById("nResult");

      if (!title) {
        out.innerHTML = '<span class="err">Title is required.</span>';
        return;
      }

      try {
        const res = await fetch("/api/news", {
          method: "POST",
          headers: headers(),
          body: JSON.stringify({ title, summary, body, category, date })
        });
        const data = await res.json();
        if (res.ok) {
          out.innerHTML = '<span class="ok">Published!</span>\\n' + JSON.stringify(data, null, 2);
          document.getElementById("nTitle").value = "";
          document.getElementById("nSummary").value = "";
          document.getElementById("nBody").value = "";
          loadNews();
        } else {
          out.innerHTML = '<span class="err">' + (data.error || "Failed") + '</span>';
          if (res.status === 401) {
            sessionStorage.removeItem("ger_admin_pwd");
            alert("Wrong password. Refresh and try again.");
          }
        }
      } catch (e) {
        out.textContent = "Network error: " + e.message;
      }
    });

    async function loadNews() {
      const box = document.getElementById("newsList");
      try {
        const res = await fetch("/api/news");
        const list = await res.json();
        if (!list.length) {
          box.innerHTML = "<p style='color:#8b949e'>No news posts yet.</p>";
          return;
        }
        box.innerHTML = list.map(n => `
          <div class="news-item">
            <div class="news-meta">${n.category || "Update"} · ${n.date || ""} · id: ${n.id}</div>
            <h4>${escapeHtml(n.title)}</h4>
            <p>${escapeHtml(n.summary || "")}</p>
            <div class="news-actions">
              <button class="danger" onclick="deleteNews('${n.id}')">Delete</button>
            </div>
          </div>
        `).join("");
      } catch (e) {
        box.textContent = "Could not load news.";
      }
    }

    window.deleteNews = async function(id) {
      if (!confirm("Delete this announcement?")) return;
      const res = await fetch("/api/news/delete", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ id })
      });
      const data = await res.json();
      if (res.ok) loadNews();
      else alert(data.error || "Delete failed");
    };

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    document.getElementById("btnCreateCode").addEventListener("click", async () => {
      const res = await fetch("/api/codes", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({
          code: document.getElementById("code").value,
          reward: document.getElementById("reward").value,
          max_uses: document.getElementById("max").value
        })
      });
      const data = await res.json();
      document.getElementById("codeResult").textContent = JSON.stringify(data, null, 2);
      if (res.ok) listCodes();
    });

    async function listCodes() {
      const res = await fetch("/api/codes", { headers: headers() });
      document.getElementById("codesList").textContent = JSON.stringify(await res.json(), null, 2);
    }

    document.getElementById("btnListCodes").addEventListener("click", listCodes);
    document.getElementById("btnRefreshNews").addEventListener("click", loadNews);

    loadNews();
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
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopped.")
        server.server_close()