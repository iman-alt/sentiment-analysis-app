from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-to-something-random-and-secret"  # used to sign session cookies

DB_PATH = os.path.join(os.path.dirname(__file__), "sentiment.db")
analyzer = SentimentIntensityAnalyzer()

# ---------- DATABASE HELPERS ----------

def get_db():
    # 'g' is a per-request storage box Flask gives you.
    # This means we only open ONE db connection per request, not one per query.
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row  # lets us access columns by name, like row["username"]
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            positive REAL NOT NULL,
            neutral REAL NOT NULL,
            negative REAL NOT NULL,
            compound REAL NOT NULL,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    db.commit()
    db.close()

# ---------- AUTH HELPER ----------

def login_required(f):
    # This is a "decorator" — it wraps a route function and runs a check BEFORE it.
    # If there's no user_id in the session, we bounce them to the login page.
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ---------- SENTIMENT HELPER ----------

def classify(compound):
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"

# ---------- ROUTES ----------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("signup"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        db = get_db()
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing:
            flash("That username is already taken.", "error")
            return redirect(url_for("signup"))

        # generate_password_hash does the one-way hashing for us — this is the
        # ONLY thing we ever store. Never store request.form["password"] directly.
        password_hash = generate_password_hash(password)

        db.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, password_hash, datetime.now().isoformat())
        )
        db.commit()

        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        # check_password_hash re-hashes the typed password internally and
        # compares it to the stored hash. We never "decrypt" the stored one.
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()  # wipes user_id and username from the session cookie
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    result = None

    if request.method == "POST":
        text = request.form["text"].strip()

        if text:
            scores = analyzer.polarity_scores(text)
            label = classify(scores["compound"])

            db = get_db()
            db.execute(
                """INSERT INTO analyses
                   (user_id, text, positive, neutral, negative, compound, label, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session["user_id"], text, scores["pos"], scores["neu"],
                 scores["neg"], scores["compound"], label, datetime.now().isoformat())
            )
            db.commit()

            result = {
                "text": text,
                "positive": round(scores["pos"] * 100, 1),
                "neutral": round(scores["neu"] * 100, 1),
                "negative": round(scores["neg"] * 100, 1),
                "compound": round(scores["compound"], 3),
                "label": label
            }

    db = get_db()
    recent = db.execute(
        "SELECT * FROM analyses WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (session["user_id"],)
    ).fetchall()

    return render_template("dashboard.html", result=result, recent=recent)

@app.route("/history")
@login_required
def history():
    db = get_db()
    analyses = db.execute(
        "SELECT * FROM analyses WHERE user_id = ? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()

    labels = [a["created_at"][:16] for a in reversed(analyses)]
    compounds = [a["compound"] for a in reversed(analyses)]

    return render_template("history.html", analyses=analyses, labels=labels, compounds=compounds)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)