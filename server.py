#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import json
import os

# Authoritative data exists on the SERVER, not in the frontend.
PROFILES = {
    "1001": {
        "profileId": "1001",
        "data": {
            "displayName": "Alice",
            "email": "alice@example.test",
            "creditLimit": 500
        }
    }
}

TOKENS = {"alice-demo-token": "1001"}

ALLOWED_PROPERTIES = {"displayName", "email"}

HTML = '''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Account Profile</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:720px;margin:0 auto;padding:28px 18px;background:#f6f7f9;color:#17202a}
.header{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px}
.header h1{font-size:22px;margin:0}
.hint{width:40px;height:40px;border-radius:50%;padding:0;border:1px solid #c8ced8;background:white;color:#17202a;font-weight:700;font-size:17px}
.card{background:white;border:1px solid #d8dde5;border-radius:14px;padding:20px}
.row{margin:0 0 18px}
label{display:block;font-size:13px;font-weight:600;margin-bottom:7px}
input{width:100%;font:inherit;padding:11px 12px;border:1px solid #c6ccd5;border-radius:9px;background:white}
input:disabled{background:#eef0f3;color:#667085;cursor:not-allowed}
.disabled-note{font-size:12px;color:#667085;margin-top:6px}
button.save{width:100%;padding:11px;border:0;border-radius:9px;background:#17202a;color:white;font:inherit;font-weight:600;cursor:pointer}
.status{margin-top:14px;font-size:13px;color:#667085}
#hintPanel{display:none;margin-top:12px;padding:12px;border-radius:9px;background:#f0f2f5;font-size:13px;color:#4b5563}
</style>
</head>
<body>
<div class="header">
  <h1>Account Profile</h1>
  <button class="hint" id="hint" title="Hint" aria-label="Hint">?</button>
</div>
<div class="card">
  <div class="row">
    <label for="displayName">Display name</label>
    <input id="displayName" value="Alice">
  </div>
  <div class="row">
    <label for="email">Email</label>
    <input id="email" value="alice@example.test">
  </div>
  <div class="row">
    <label for="creditLimit">Credit limit</label>
    <input id="creditLimit" value="$500" disabled>
    <div class="disabled-note">This field cannot be edited.</div>
  </div>
  <button class="save" id="save">Save changes</button>
  <div class="status" id="status"></div>
</div>
<div id="hintPanel">
  Inspect the request generated when saving editable profile data.
</div>
<script>
const TOKEN = "alice-demo-token";
async function loadProfile(){
  const r = await fetch("/api/profiles/1001", {
    headers: {"Authorization": "Bearer " + TOKEN}
  });
  const result = await r.json();
  if(result.profile){
    document.getElementById("displayName").value = result.profile.data.displayName || "";
    document.getElementById("email").value = result.profile.data.email || "";
    document.getElementById("creditLimit").value = "$" + result.profile.data.creditLimit;
  }
}
async function save(){
  const body = {
    profileId: "1001",
    data: {
      displayName: document.getElementById("displayName").value,
      email: document.getElementById("email").value
    }
  };
  const r = await fetch("/api/profiles/1001", {
    method:"PATCH",
    headers:{
      "Authorization":"Bearer " + TOKEN,
      "Content-Type":"application/json"
    },
    body:JSON.stringify(body)
  });
  document.getElementById("status").textContent =
    r.ok ? "Changes saved." : "Unable to save changes.";
  if(r.ok) await loadProfile();
}
document.getElementById("save").addEventListener("click",save);
document.getElementById("hint").addEventListener("click",function(){
  const p=document.getElementById("hintPanel");
  p.style.display=p.style.display==="block" ? "none" : "block";
});
loadProfile();
</script>
</body>
</html>'''

def send_json(handler, status, obj):
    data = json.dumps(obj, indent=2).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def authenticate(handler):
    value = handler.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        return None
    return TOKENS.get(value[7:].strip())

def reset_data():
    PROFILES["1001"]["data"] = {
        "displayName": "Alice",
        "email": "alice@example.test",
        "creditLimit": 500
    }

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            data = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        if path == "/api/profiles/1001":
            user_id = authenticate(self)
            if user_id is None:
                return send_json(self, 401, {"error":"unauthorized"})
            if user_id != "1001":
                return send_json(self, 403, {"error":"forbidden"})
            return send_json(self, 200, {
                "status":200,
                "profile":PROFILES["1001"]
            })

        return send_json(self, 404, {"error":"not found"})

    def do_PATCH(self):
        if urlparse(self.path).path != "/api/profiles/1001":
            return send_json(self, 404, {"error":"not found"})

        user_id = authenticate(self)
        if user_id is None:
            return send_json(self, 401, {"error":"unauthorized"})
        if user_id != "1001":
            return send_json(self, 403, {"error":"forbidden"})

        try:
            length = int(self.headers.get("Content-Length","0"))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return send_json(self, 400, {"error":"invalid JSON"})

        if body.get("profileId") != "1001":
            return send_json(self, 403, {
                "error":"profileId must match authenticated profile"
            })

        data = body.get("data")
        if not isinstance(data, dict) or not data:
            return send_json(self, 400, {"error":"data object required"})

        # INTENTIONALLY VULNERABLE:
        # Authentication and object authorization pass, but properties inside
        # data are not individually authorized.
        PROFILES["1001"]["data"].update(data)

        return send_json(self, 200, {
            "status":200,
            "profile":PROFILES["1001"]
        })

    def do_POST(self):
        if urlparse(self.path).path != "/api/reset":
            return send_json(self, 404, {"error":"not found"})
        reset_data()
        return send_json(self, 200, {"message":"reset complete"})

    def log_message(self, fmt, *args):
        print("[HTTP]", fmt % args)

if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT","8000"))
    print(f"BOPLA Lab listening on http://{host}:{port}")
    ThreadingHTTPServer((host,port),Handler).serve_forever()
