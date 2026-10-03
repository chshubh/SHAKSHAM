import json
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from logic.progress_tracker import minutes_by_day, minutes_by_week, streak
from logic.recommendation import recommend_exercises
from logic.safety_checker import RED_FLAGS, safety_check
from logic.workout_generator import GOAL_LABELS, LIM_LABELS, build_workout

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.config.from_object(Config)

GOALS = list(GOAL_LABELS)
RATINGS = ["easy", "moderate", "difficult", "pain"]
SEVERITY = {"easy": 1, "moderate": 2, "difficult": 3, "pain": 4}

ACHIEVEMENTS = [
    ("first_assessment", "Getting Started", "Completed your first assessment."),
    ("first_session", "First Step", "Finished your first workout."),
    ("three_sessions", "Finding a Rhythm", "Completed 3 workouts."),
    ("ten_sessions", "Consistency", "Completed 10 workouts."),
    ("streak_3", "Three in a Row", "Moved on 3 days in a row."),
    ("minutes_60", "One Hour of Movement", "Reached 60 total active minutes."),
    ("listened", "Listening to Your Body", "Stopped a session when something didn't feel right. That's a smart call."),
]


# ---------- database ----------
def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with open(os.path.join(BASE, "database", "schema.sql")) as f:
        db.executescript(f.read())
    with open(os.path.join(BASE, "data", "exercises.json")) as f:
        for ex in json.load(f):
            db.execute(
                """INSERT INTO exercises (slug, name, category, difficulty, data_json) VALUES (?,?,?,?,?)
                   ON CONFLICT(slug) DO UPDATE SET name=excluded.name, category=excluded.category,
                   difficulty=excluded.difficulty, data_json=excluded.data_json""",
                (ex["id"], ex["name"], ex["categories"][0], ex["difficulty"], json.dumps(ex)))
    for code, name, desc in ACHIEVEMENTS:
        db.execute("INSERT OR IGNORE INTO achievements (code, name, description) VALUES (?,?,?)", (code, name, desc))
    db.commit()
    if not db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        seed_demo(db)


def ex_from_row(r):
    d = json.loads(r["data_json"])
    d["id"] = r["slug"]
    return d


def all_exercises():
    return [ex_from_row(r) for r in get_db().execute("SELECT * FROM exercises ORDER BY name")]


def get_exercise(slug):
    r = get_db().execute("SELECT * FROM exercises WHERE slug=?", (slug,)).fetchone()
    return ex_from_row(r) if r else None


# ---------- auth / security ----------
def current_user():
    uid = session.get("uid")
    if uid is None:
        return None
    if not hasattr(g, "_user"):
        g._user = get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return g._user


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if not current_user():
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


@app.before_request
def csrf_protect():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    if request.method == "POST":
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or not secrets.compare_digest(token, session["csrf"]):
            abort(400, "Invalid or missing form token. Please go back and try again.")


@app.context_processor
def inject():
    u = current_user()
    classes = []
    if u:
        classes += [f"text-{u['text_size'] or 'normal'}"]
        if u["high_contrast"]:
            classes.append("hc")
        if u["reduce_motion"]:
            classes.append("reduce-motion")
    return {"user": u, "csrf_token": session.get("csrf", ""), "body_class": " ".join(classes),
            "GOAL_LABELS": GOAL_LABELS, "LIM_LABELS": LIM_LABELS}


@app.template_filter("pretty")
def pretty(s):
    return str(s).replace("_", " ").capitalize()


@app.template_filter("nice_date")
def nice_date(s):
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        return s


# ---------- stats / achievements ----------
def user_stats(uid):
    db = get_db()
    rows = db.execute("SELECT * FROM workout_sessions WHERE user_id=? AND completed=1", (uid,)).fetchall()
    pairs = [(datetime.strptime(r["created_at"][:10], "%Y-%m-%d").date(), r["duration_seconds"]) for r in rows]
    # minutes also count for partially completed sessions
    part = db.execute("SELECT created_at, duration_seconds FROM workout_sessions WHERE user_id=?", (uid,)).fetchall()
    all_pairs = [(datetime.strptime(r["created_at"][:10], "%Y-%m-%d").date(), r["duration_seconds"]) for r in part]
    days = {d for d, _ in pairs}
    return {
        "sessions": len(rows),
        "total_minutes": round(sum(s for _, s in all_pairs) / 60),
        "streak": streak(days),
        "active_days": len(days),
        "week": minutes_by_day(all_pairs),
        "weeks": minutes_by_week(all_pairs),
        "paused": db.execute("SELECT COUNT(*) c FROM workout_sessions WHERE user_id=? AND feedback='pain'", (uid,)).fetchone()["c"],
        "has_assessment": db.execute("SELECT COUNT(*) c FROM assessments WHERE user_id=?", (uid,)).fetchone()["c"] > 0,
    }


def check_achievements(uid):
    db, s = get_db(), user_stats(uid)
    rules = {
        "first_assessment": s["has_assessment"], "first_session": s["sessions"] >= 1,
        "three_sessions": s["sessions"] >= 3, "ten_sessions": s["sessions"] >= 10,
        "streak_3": s["streak"] >= 3, "minutes_60": s["total_minutes"] >= 60, "listened": s["paused"] >= 1,
    }
    new = []
    for code, ok in rules.items():
        if not ok:
            continue
        a = db.execute("SELECT * FROM achievements WHERE code=?", (code,)).fetchone()
        cur = db.execute("INSERT OR IGNORE INTO user_achievements (user_id, achievement_id, earned_at) VALUES (?,?,?)",
                         (uid, a["id"], now()))
        if cur.rowcount:
            new.append(a["name"])
    db.commit()
    return new


# ---------- assessment helpers ----------
def latest_assessment(uid):
    r = get_db().execute("SELECT * FROM assessments WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    if not r:
        return None
    return {"id": r["id"], "blocked": bool(r["safety_block"]), "data": json.loads(r["data_json"]), "created_at": r["created_at"]}


def create_plan(uid, assessment_id, a):
    profile = {
        "goal": a["goal"], "difficulty": a["experience"], "equipment": a["equipment"],
        "limitations": a["limitations"], "health_status": a.get("health_status"), "safety_block": False,
    }
    eligible, report = recommend_exercises(profile, all_exercises())
    w = build_workout(eligible, profile, int(a["duration"]), report)
    db = get_db()
    cur = db.execute(
        "INSERT INTO workout_plans (user_id, assessment_id, name, goal, duration_minutes, explanation_json, created_at) VALUES (?,?,?,?,?,?,?)",
        (uid, assessment_id, f"{GOAL_LABELS[a['goal']]} routine", a["goal"], w["estimated_minutes"],
         json.dumps({"notes": w["notes"]}), now()))
    pid = cur.lastrowid
    for i, e in enumerate(w["exercises"]):
        db.execute(
            "INSERT INTO workout_exercises (plan_id, exercise_slug, position_order, role, sets, reps, duration_seconds, rest_seconds, why) VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, e["slug"], i, e["role"], e["sets"], e["reps"], e["duration_seconds"], e["rest_seconds"], e["why"]))
    db.commit()
    return pid


def load_plan(pid, uid=None):
    db = get_db()
    p = db.execute("SELECT * FROM workout_plans WHERE id=?" + (" AND user_id=?" if uid else ""),
                   (pid, uid) if uid else (pid,)).fetchone()
    if not p:
        return None
    items = []
    for r in db.execute("SELECT * FROM workout_exercises WHERE plan_id=? ORDER BY position_order", (pid,)):
        ex = get_exercise(r["exercise_slug"])
        if ex:
            items.append({**dict(r), "ex": ex})
    return {"row": p, "steps": items, "notes": json.loads(p["explanation_json"] or "{}").get("notes", [])}


def parse_assessment(f):
    errors = []
    req = {"age_group": "age group", "experience": "fitness experience", "activity_level": "activity level",
           "duration": "workout length", "goal": "goal", "health_status": "health status", "injury_status": "injury status",
           "professional_restriction": "answer about professional exercise restrictions"}
    for k, label in req.items():
        if not f.get(k):
            errors.append(f"Please choose your {label}.")
    lims = f.getlist("limitations")
    if not lims:
        errors.append("Please choose at least one option for your current physical ability (or 'None').")
    if "none" in lims:
        lims = []
    for c in f.getlist("conditions"):
        if c in ("joint_discomfort", "back_discomfort"):
            lims.append(c)
    if not f.get("confirm"):
        errors.append("Please confirm that you've read the disclaimer.")
    a = {
        "age_group": f.get("age_group"), "experience": f.get("experience"), "activity_level": f.get("activity_level"),
        "duration": f.get("duration") if f.get("duration") in ("10", "15", "20", "30") else "15",
        "equipment": [e for e in f.getlist("equipment") if e in ("chair", "resistance_band", "light_weights")],
        "goal": f.get("goal") if f.get("goal") in GOALS else None,
        "limitations": sorted(set(l for l in lims if l in LIM_LABELS)),
        "none_selected": "none" in f.getlist("limitations"),
        "health_status": f.get("health_status"), "injury_status": f.get("injury_status"),
        "conditions": [c for c in f.getlist("conditions") if c in ("joint_discomfort", "back_discomfort")],
        "chest_pain": "chest_pain" in f.getlist("symptoms"), "fainting": "fainting" in f.getlist("symptoms"),
        "severe_breathlessness": "severe_breathlessness" in f.getlist("symptoms"),
        "severe_acute_pain": "severe_acute_pain" in f.getlist("symptoms"),
        "recent_serious_injury": f.get("injury_status") == "recent_serious",
        "professional_exercise_restriction": f.get("professional_restriction") == "yes",
    }
    return a, errors


# ---------- public pages ----------
@app.route("/")
def index():
    return render_template("index.html", exercises=all_exercises()[:3])


@app.route("/exercises")
def exercises():
    q, cat, diff, pos = (request.args.get(k, "").strip() for k in ("q", "category", "difficulty", "position"))
    items = all_exercises()
    if q:
        items = [e for e in items if q.lower() in e["name"].lower() or any(q.lower() in t for t in e["target_area"])]
    if cat:
        items = [e for e in items if cat in e["categories"]]
    if diff:
        items = [e for e in items if e["difficulty"] == diff]
    if pos:
        items = [e for e in items if e["position"] == pos]
    return render_template("exercises.html", items=items, q=q, cat=cat, diff=diff, pos=pos)


@app.route("/exercise/<slug>")
def exercise_detail(slug):
    ex = get_exercise(slug)
    if not ex:
        abort(404)
    return render_template("exercise_detail.html", ex=ex)


# ---------- auth ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name, email = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower()
        pw = request.form.get("password", "")
        err = None
        if not name or "@" not in email:
            err = "Please enter your name and a valid email."
        elif len(pw) < 8:
            err = "Password must be at least 8 characters."
        elif get_db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            err = "An account with that email already exists. Try logging in."
        if err:
            flash(err, "error")
            return render_template("register.html", name=name, email=email), 400
        cur = get_db().execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?,?,?,?)",
                               (name, email, generate_password_hash(pw), now()))
        get_db().commit()
        session.clear()
        session["uid"] = cur.lastrowid
        flash(f"Welcome, {name}! Let's set up your movement plan.", "success")
        return redirect(url_for("assessment"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if u and check_password_hash(u["password_hash"], request.form.get("password", "")):
            session.clear()
            session["uid"] = u["id"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
        flash("Email or password didn't match. Please try again.", "error")
        return render_template("login.html", email=email), 401
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))


# ---------- assessment ----------
@app.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    uid = current_user()["id"]
    if request.method == "POST":
        a, errors = parse_assessment(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("assessment.html", a=a, flags=RED_FLAGS), 400
        result = safety_check(a)
        db = get_db()
        cur = db.execute("INSERT INTO assessments (user_id, data_json, safety_block, created_at) VALUES (?,?,?,?)",
                         (uid, json.dumps(a), 0 if result["safe_to_generate"] else 1, now()))
        db.commit()
        if result["safe_to_generate"]:
            create_plan(uid, cur.lastrowid, a)
            flash("Your personalised routine is ready.", "success")
        else:
            flash("We've paused your plan for safety. See the message below.", "info")
        for n in check_achievements(uid):
            flash(f"Achievement unlocked: {n}", "success")
        return redirect(url_for("dashboard"))
    last = latest_assessment(uid)
    return render_template("assessment.html", a=last["data"] if last else {}, flags=RED_FLAGS)


# ---------- dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    u = current_user()
    la = latest_assessment(u["id"])
    stats = user_stats(u["id"])
    plan = None
    safety = None
    if la and la["blocked"]:
        safety = safety_check(la["data"])
    elif la:
        r = get_db().execute("SELECT id FROM workout_plans WHERE user_id=? ORDER BY id DESC LIMIT 1", (u["id"],)).fetchone()
        plan = load_plan(r["id"]) if r else None
    recent = get_db().execute(
        "SELECT * FROM exercise_feedback WHERE user_id=? ORDER BY id DESC LIMIT 5", (u["id"],)).fetchall()
    recent = [{**dict(r), "name": (get_exercise(r["exercise_slug"]) or {}).get("name", r["exercise_slug"])} for r in recent]
    last_pain = get_db().execute("SELECT feedback FROM workout_sessions WHERE user_id=? ORDER BY id DESC LIMIT 1",
                                 (u["id"],)).fetchone()
    return render_template("dashboard.html", la=la, stats=stats, plan=plan, safety=safety, recent=recent,
                           caution=bool(last_pain and last_pain["feedback"] == "pain"))


# ---------- workout ----------
@app.route("/workout/<int:pid>")
@login_required
def workout(pid):
    uid = current_user()["id"]
    la = latest_assessment(uid)
    if la and la["blocked"]:
        flash("Workouts are paused until you've completed a new safety screening.", "info")
        return redirect(url_for("dashboard"))
    plan = load_plan(pid, uid)
    if not plan or not plan["steps"]:
        abort(404)
    payload = {"planId": pid, "csrf": session["csrf"], "exercises": [
        {"slug": i["exercise_slug"], "name": i["ex"]["name"], "sets": i["sets"], "reps": i["reps"],
         "duration": i["duration_seconds"], "rest": i["rest_seconds"], "instructions": i["ex"]["instructions"],
         "breathing": i["ex"]["breathing_tip"], "mods": i["ex"]["common_modifications"],
         "safety": i["ex"]["safety_notes"], "position": i["ex"]["position"], "role": i["role"]} for i in plan["steps"]]}
    return render_template("workout.html", plan=plan, payload=payload)


@app.route("/workout/<int:pid>/feedback", methods=["POST"])
@login_required
def workout_feedback(pid):
    uid = current_user()["id"]
    d = request.get_json(silent=True) or {}
    if not load_plan(pid, uid) or d.get("rating") not in RATINGS or not get_exercise(d.get("exercise", "")):
        return jsonify(ok=False), 400
    get_db().execute("INSERT INTO exercise_feedback (user_id, plan_id, exercise_slug, rating, created_at) VALUES (?,?,?,?,?)",
                     (uid, pid, d["exercise"], d["rating"], now()))
    get_db().commit()
    return jsonify(ok=True, stop=d["rating"] == "pain")


@app.route("/workout/<int:pid>/complete", methods=["POST"])
@login_required
def workout_complete(pid):
    uid = current_user()["id"]
    if not load_plan(pid, uid):
        return jsonify(ok=False), 404
    d = request.get_json(silent=True) or {}
    secs = max(0, min(int(d.get("duration_seconds") or 0), 4 * 3600))
    completed = bool(d.get("completed"))
    db = get_db()
    pending = db.execute("SELECT * FROM exercise_feedback WHERE user_id=? AND plan_id=? AND session_id IS NULL",
                         (uid, pid)).fetchall()
    if secs < 20 and not completed and not pending:
        return jsonify(ok=True, recorded=False)
    worst = max((r["rating"] for r in pending), key=lambda r: SEVERITY[r], default=None)
    cur = db.execute("INSERT INTO workout_sessions (user_id, plan_id, duration_seconds, completed, feedback, created_at) VALUES (?,?,?,?,?,?)",
                     (uid, pid, secs, 1 if completed else 0, worst, now()))
    db.execute("UPDATE exercise_feedback SET session_id=? WHERE user_id=? AND plan_id=? AND session_id IS NULL",
               (cur.lastrowid, uid, pid))
    db.commit()
    return jsonify(ok=True, recorded=True, achievements=check_achievements(uid))


# ---------- progress / achievements / profile ----------
@app.route("/progress")
@login_required
def progress():
    uid = current_user()["id"]
    db = get_db()
    sessions = db.execute("SELECT * FROM workout_sessions WHERE user_id=? ORDER BY id DESC LIMIT 12", (uid,)).fetchall()
    dist = {r["rating"]: r["c"] for r in db.execute(
        "SELECT rating, COUNT(*) c FROM exercise_feedback WHERE user_id=? GROUP BY rating", (uid,))}
    return render_template("progress.html", stats=user_stats(uid), sessions=sessions, dist=dist)


@app.route("/achievements")
@login_required
def achievements():
    uid = current_user()["id"]
    rows = get_db().execute(
        """SELECT a.*, ua.earned_at FROM achievements a
           LEFT JOIN user_achievements ua ON ua.achievement_id=a.id AND ua.user_id=? ORDER BY a.id""", (uid,)).fetchall()
    return render_template("achievements.html", rows=rows)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    u = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip() or u["name"]
        size = request.form.get("text_size") if request.form.get("text_size") in ("normal", "large", "xlarge") else "normal"
        get_db().execute("UPDATE users SET name=?, text_size=?, high_contrast=?, reduce_motion=? WHERE id=?",
                         (name, size, 1 if request.form.get("high_contrast") else 0,
                          1 if request.form.get("reduce_motion") else 0, u["id"]))
        get_db().commit()
        flash("Your settings were saved.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", la=latest_assessment(u["id"]))


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, msg="We couldn't find that page."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request.")), 400


# ---------- demo data ----------
def seed_demo(db):
    cur = db.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?,?,?,?)",
                     ("Demo User", "demo@shaksham.app", generate_password_hash("Demo@1234"), now()))
    uid = cur.lastrowid
    a = {"age_group": "45-59", "experience": "beginner", "activity_level": "light", "duration": "15",
         "equipment": ["chair"], "goal": "mobility", "limitations": ["balance"], "none_selected": False,
         "health_status": "good", "injury_status": "none", "conditions": [], "chest_pain": False, "fainting": False,
         "severe_breathlessness": False, "severe_acute_pain": False, "recent_serious_injury": False,
         "professional_exercise_restriction": False}
    aid = db.execute("INSERT INTO assessments (user_id, data_json, safety_block, created_at) VALUES (?,?,0,?)",
                     (uid, json.dumps(a), now())).lastrowid
    db.commit()
    pid = create_plan(uid, aid, a)
    slugs = [r["exercise_slug"] for r in db.execute("SELECT exercise_slug FROM workout_exercises WHERE plan_id=?", (pid,))]
    ratings = ["easy", "moderate", "moderate", "easy", "difficult"]
    for n, off in enumerate([1, 2, 3, 5, 6, 9, 10, 13, 16, 22, 30]):
        ts = (datetime.now() - timedelta(days=off)).replace(hour=8, minute=30).strftime("%Y-%m-%d %H:%M:%S")
        secs = (11 + n % 5) * 60
        sid = db.execute("INSERT INTO workout_sessions (user_id, plan_id, duration_seconds, completed, feedback, created_at) VALUES (?,?,?,1,?,?)",
                         (uid, pid, secs, ratings[n % 5], ts)).lastrowid
        db.execute("INSERT INTO exercise_feedback (user_id, plan_id, session_id, exercise_slug, rating, created_at) VALUES (?,?,?,?,?,?)",
                   (uid, pid, sid, slugs[n % len(slugs)], ratings[n % 5], ts))
    db.commit()
    check_achievements(uid)


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
