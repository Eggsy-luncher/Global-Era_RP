#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime
import json, os, uuid

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
            {"id": "1", "title": "Game Launch Announcement", "summary": "Release timeline and server details.", "body": "", "date": "2026-08-01", "category": "Coming Soon"},
            {"id": "2", "title": "Community Preparations", "summary": "Guides, rewards, and store info.", "body": "", "date": "2026-08-05", "category": "New"},
            {"id": "3", "title": "What to Expect", "summary": "Features highlighted before launch.", "body": "", "date": "2026-08-08", "category": "Info"},
        ])
    if not os.path.exists(REWARDS_FILE):
        save_json(REWARDS_FILE, {"rewards": [
            {"day": 1, "reward": "50 State Coins"}, {"day": 2, "reward": "100 State Coins"},
            {"day": 3, "reward": "Starter Pack"}, {"day": 4, "reward": "150 State Coins"},
            {"day": 5, "reward": "Random Case"}, {"day": 6, "reward": "200 State Coins"},
            {"day": 7, "reward": "Premium Bundle"}], "cooldown_hours": 20})
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

    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def get_ip(self):
        x = self.headers.get("X-Forwarded-For")
        return x.split(",")[0].strip() if x else self.client_address[0]

    def is_admin(self):
        return (self.headers.get("X-Admin-Password") or "") == ADMIN_PASSWORD

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            return self.json_response({"status": "ok", "server": "Global Era RP Backend"})
        if path == "/api/news":
            return self.json_response(load_json(NEWS_FILE, []))
        if path == "/api/rewards":
            return self.json_response(load_json(REWARDS_FILE, {}))
        if path == "/api/rewards/status":
            return self.rewards_status()
        if path == "/api/codes":
            if not self.is_admin():
                return self.json_response({"error": "Unauthorized"}, 401)
            return self.json_response(load_json(REDEEM_FILE, []))
        if path == "/admin":
            return self.admin_page()
        if path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        data = self.read_body()
        if path == "/api/redeem":
            return self.redeem(data)
        if path == "/api/rewards/claim":
            return self.claim()
        if path == "/api/codes":
            return self.create_code(data)
        if path == "/api/news":
            return self.add_news(data)
        if path == "/api/news/delete":
            return self.delete_news(data)
        self.send_error(404)

    def redeem(self, data):
        code = (data.get("code") or "").strip().upper()
        if not code:
            return self.json_response({"success": False, "message": "Enter a code."}, 400)
        codes = load_json(REDEEM_FILE, [])
        found = next((c for c in codes if c["code"].upper() == code), None)
        if not found:
            return self.json_response({"success": False, "message": "Invalid code."}, 404)
        if not found.get("active", True) or found["used"] >= found["max_uses"]:
            return self.json_response({"success": False, "message": "Code unavailable."}, 400)
        found["used"] += 1
        save_json(REDEEM_FILE, codes)
        return self.json_response({"success": True, "message": "Success! You received: " + found["reward"], "reward": found["reward"]})

    def rewards_status(self):
        ip = self.get_ip()
        claims = load_json(CLAIMS_FILE, {})
        config = load_json(REWARDS_FILE, {})
        p = claims.get(ip, {"last_claim": None, "streak": 0, "total_claims": 0})
        can, left = True, 0
        if p.get("last_claim"):
            hours = (datetime.utcnow() - datetime.fromisoformat(p["last_claim"])).total_seconds() / 3600
            cd = config.get("cooldown_hours", 20)
            if hours < cd:
                can, left = False, round(cd - hours, 1)
        return self.json_response({"can_claim": can, "streak": p.get("streak", 0), "total_claims": p.get("total_claims", 0), "next_claim_in_hours": left})

    def claim(self):
        ip = self.get_ip()
        claims = load_json(CLAIMS_FILE, {})
        config = load_json(REWARDS_FILE, {})
        cd = config.get("cooldown_hours", 20)
        now = datetime.utcnow()
        p = claims.get(ip, {"last_claim": None, "streak": 0, "total_claims": 0})
        if p.get("last_claim"):
            hours = (now - datetime.fromisoformat(p["last_claim"])).total_seconds() / 3600
            if hours < cd:
                return self.json_response({"success": False, "message": "Wait " + str(round(cd - hours, 1)) + " hours.", "next_claim_in_hours": round(cd - hours, 1)}, 429)
            p["streak"] = p.get("streak", 0) + 1 if hours < 48 else 1
        else:
            p["streak"] = 1
        p["total_claims"] = p.get("total_claims", 0) + 1
        p["last_claim"] = now.isoformat()
        day = ((p["streak"] - 1) % 7) + 1
        reward = next((r for r in config.get("rewards", []) if r["day"] == day), {"reward": "50 State Coins"})
        claims[ip] = p
        save_json(CLAIMS_FILE, claims)
        return self.json_response({"success": True, "message": "Day " + str(day) + " claimed!", "reward": reward["reward"], "streak": p["streak"], "total_claims": p["total_claims"]})

    def create_code(self, data):
        if not self.is_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        code = (data.get("code") or "").strip().upper()
        if not code:
            return self.json_response({"error": "Code required"}, 400)
        codes = load_json(REDEEM_FILE, [])
        item = {"code": code, "reward": data.get("reward", "Reward"), "max_uses": int(data.get("max_uses", 100)), "used": 0, "active": True}
        codes.append(item)
        save_json(REDEEM_FILE, codes)
        return self.json_response(item, 201)

    def add_news(self, data):
        if not self.is_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        news = load_json(NEWS_FILE, [])
        item = {
            "id": str(uuid.uuid4())[:8],
            "title": (data.get("title") or "Untitled").strip(),
            "summary": (data.get("summary") or "").strip(),
            "body": (data.get("body") or "").strip(),
            "date": data.get("date") or datetime.now().strftime("%Y-%m-%d"),
            "category": (data.get("category") or "Update").strip()
        }
        news.insert(0, item)
        save_json(NEWS_FILE, news)
        return self.json_response(item, 201)

    def delete_news(self, data):
        if not self.is_admin():
            return self.json_response({"error": "Unauthorized"}, 401)
        nid = (data.get("id") or "").strip()
        news = load_json(NEWS_FILE, [])
        new_list = [n for n in news if n.get("id") != nid]
        if len(new_list) == len(news):
            return self.json_response({"error": "Not found"}, 404)
        save_json(NEWS_FILE, new_list)
        return self.json_response({"success": True})

    def admin_page(self):
        html = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin</title><style>
body{font-family:Arial;background:#0d1117;color:#eee;padding:20px;max-width:700px;margin:auto}
h1,h2{color:#f5cf22}.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin:12px 0}
input,textarea,select,button{width:100%;padding:10px;margin:6px 0;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#fff;box-sizing:border-box}
button{background:#f5cf22;color:#000;font-weight:bold;border:0;cursor:pointer}
button.danger{background:#da3633;color:#fff;width:auto}
.item{background:#0d1117;border:1px solid #30363d;padding:10px;margin:8px 0;border-radius:6px}
.ok{color:#3dd68c}.err{color:#ff6b6b}
</style></head><body>
<h1>GLOBAL ERA RP Admin</h1>
<div class="card"><h2>Publish News</h2>
<input id="title" placeholder="Title">
<select id="category"><option>Update</option><option>Event</option><option>Announcement</option><option>Info</option></select>
<input id="summary" placeholder="Short summary">
<textarea id="body" rows="4" placeholder="Full text"></textarea>
<button onclick="publish()">Publish</button><pre id="result"></pre></div>
<div class="card"><h2>News List</h2><button onclick="loadNews()" style="width:auto">Refresh</button><div id="list"></div></div>
<div class="card"><h2>Redeem Code</h2>
<input id="code" placeholder="CODE"><input id="reward" placeholder="Reward">
<input id="max" type="number" value="100"><button onclick="createCode()">Create</button><pre id="codeOut"></pre></div>
<script>
let pwd=sessionStorage.getItem("pwd")||prompt("Admin password:")||"";
sessionStorage.setItem("pwd",pwd);
const H=()=>({"Content-Type":"application/json","X-Admin-Password":pwd});
async function publish(){
  const r=await fetch("/api/news",{method:"POST",headers:H(),body:JSON.stringify({title:title.value,category:category.value,summary:summary.value,body:body.value})});
  const d=await r.json();
  result.innerHTML=r.ok?'<span class="ok">Published</span>':'<span class="err">'+(d.error||"fail")+'</span>';
  if(r.ok){title.value="";summary.value="";body.value="";loadNews();}
}
async function loadNews(){
  const list=await(await fetch("/api/news")).json();
  const box=document.getElementById("list");
  if(!list.length){box.innerHTML="No posts";return;}
  box.innerHTML=list.map(n=>'<div class="item"><b>'+n.title+'</b><br><small>'+n.category+' · '+n.date+'</small><br>'+(n.summary||'')+'<br><button class="danger" data-id="'+n.id+'">Delete</button></div>').join("");
  box.querySelectorAll("button.danger").forEach(b=>b.onclick=()=>del(b.getAttribute("data-id")));
}
async function del(id){
  if(!confirm("Delete?"))return;
  await fetch("/api/news/delete",{method:"POST",headers:H(),body:JSON.stringify({id:id})});
  loadNews();
}
async function createCode(){
  const r=await fetch("/api/codes",{method:"POST",headers:H(),body:JSON.stringify({code:code.value,reward:reward.value,max_uses:max.value})});
  codeOut.textContent=JSON.stringify(await r.json(),null,2);
}
loadNews();
</script></body></html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[" + datetime.now().strftime("%H:%M:%S") + "]", args[0])

if __name__ == "__main__":
    print("Global Era RP on port", PORT)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()