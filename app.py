"""
Deliberately vulnerable Flask app for CSRF demonstration.
Run: python app.py
Then open http://127.0.0.1:5000
"""
from flask import Flask, request, session, redirect, url_for, render_template_string

app = Flask(__name__)
app.secret_key = "demo-secret"   # fixed key so session survives reloads

# ── In-memory "database" ─────────────────────────────────────────────────
users = {
    "alice": {"password": "password123", "display_name": "Alice", "email": "alice@example.com"}
}

# ── Templates ─────────────────────────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html><html><head>
<title>SecureBank – Login</title>
<style>
  body{font-family:Segoe UI,sans-serif;background:#f0f4ff;display:grid;place-items:center;min-height:100vh;margin:0}
  .card{background:#fff;padding:2rem 2.5rem;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.1);width:320px}
  h2{margin:0 0 1.2rem;color:#1e3a8a}
  input{width:100%;padding:.55rem .75rem;margin-bottom:.9rem;border:1px solid #d1d5db;border-radius:6px;font-size:.95rem;box-sizing:border-box}
  button{width:100%;padding:.6rem;background:#1d4ed8;color:#fff;border:none;border-radius:6px;font-size:1rem;cursor:pointer}
  .err{color:#dc2626;font-size:.85rem;margin-bottom:.75rem}
</style></head><body>
<div class="card">
  <h2>🏦 SecureBank Login</h2>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST" action="/login">
    <input name="username" placeholder="Username (alice)" value="alice"/>
    <input name="password" type="password" placeholder="Password (password123)" value="password123"/>
    <button type="submit">Log In</button>
  </form>
</div>
</body></html>
"""

PROFILE_HTML = """
<!DOCTYPE html><html><head>
<title>SecureBank – Profile</title>
<style>
  body{font-family:Segoe UI,sans-serif;background:#f0f4ff;display:grid;place-items:center;min-height:100vh;margin:0}
  .card{background:#fff;padding:2rem 2.5rem;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.1);width:440px}
  h2{margin:0 0 .3rem;color:#1e3a8a}
  .sub{color:#6b7280;font-size:.85rem;margin-bottom:1.2rem}
  .info{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:.9rem 1.1rem;margin-bottom:1.2rem}
  .info b{color:#166534}
  label{display:block;font-size:.85rem;color:#374151;margin-bottom:.3rem;font-weight:600}
  input[type=text],input[type=email]{width:100%;padding:.5rem .75rem;border:1px solid #d1d5db;border-radius:6px;
         font-size:.95rem;box-sizing:border-box;margin-bottom:.9rem}
  button{padding:.55rem 1.2rem;background:#1d4ed8;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:.95rem}
  .logout{float:right;background:#f3f4f6;color:#374151;border:1px solid #d1d5db}
  .warn{background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:.75rem 1rem;
        font-size:.82rem;color:#991b1b;margin-top:1rem}
</style></head><body>
<div class="card">
  <h2>👤 My Profile</h2>
  <div class="sub">Logged in as <strong>{{ username }}</strong>
    <form method="POST" action="/logout" style="display:inline;float:right">
      <button class="logout" type="submit">Logout</button>
    </form>
  </div>

  <div class="info">
    <b>Display name:</b> {{ display_name }}<br>
    <b>Email:</b> {{ email }}
  </div>

  <!-- ⚠ Vulnerable form — no CSRF token -->
  <form method="POST" action="/update-profile">
    <label>Display Name</label>
    <input type="text"  name="display_name" value="{{ display_name }}"/>
    <label>Email</label>
    <input type="email" name="email"         value="{{ email }}"/>
    <button type="submit">Update Profile</button>
  </form>

  <div class="warn">
    ⚠ This form has <strong>no CSRF token</strong>.<br>
    Open <a href="http://127.0.0.1:5500/csrf_poc.html" target="_blank">
    the attacker page</a> (port 5500) while logged in to trigger the attack.
  </div>
</div>
</body></html>
"""

# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("profile"))


@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        if u in users and users[u]["password"] == p:
            session["username"] = u
            return redirect(url_for("profile"))
        error = "Invalid credentials."
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))
    u = session["username"]
    return render_template_string(PROFILE_HTML,
        username=u,
        display_name=users[u]["display_name"],
        email=users[u]["email"])


@app.route("/update-profile", methods=["POST"])
def update_profile():
    """⚠ Vulnerable endpoint — accepts POST with no CSRF check."""
    if "username" not in session:
        return "Not logged in", 403
    u = session["username"]
    dn = request.form.get("display_name", users[u]["display_name"])
    em = request.form.get("email",        users[u]["email"])
    users[u]["display_name"] = dn
    users[u]["email"]        = em
    print(f"[UPDATE] {u} → display_name='{dn}', email='{em}'")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    print("\n  🏦  Vulnerable lab running at http://127.0.0.1:5000")
    print("  Login: alice / password123\n")
    app.run(debug=True, port=5000)
