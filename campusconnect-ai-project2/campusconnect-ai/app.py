"""CampusConnect AI - student issue platform (Flask).
Workflow: student submits -> AI suggests category/department/priority -> official reviews
-> action and status update -> student is notified. AI assists; humans decide."""
import functools
import os
import re
import secrets
from datetime import date, datetime

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import ai
import db

PRIORITIES = ["low", "medium", "high"]
STATUSES = ["submitted", "under_review", "in_progress", "needs_info", "resolved", "closed"]
OPEN_STATUSES = ["submitted", "under_review", "in_progress", "needs_info"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.getenv("DATABASE", "campusconnect.db"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)
    app.teardown_appcontext(db.close_db)
    with app.app_context():
        db.init_db()

    # ---------- helpers ----------
    @app.before_request
    def load_user():
        uid = session.get("user_id")
        g.user = db.get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone() if uid else None

    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
            if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
                abort(400, "Invalid or missing CSRF token")

    @app.context_processor
    def inject():
        if "_csrf" not in session:
            session["_csrf"] = secrets.token_hex(16)
        unread = 0
        if g.get("user"):
            unread = db.get_db().execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (g.user["id"],)
            ).fetchone()[0]
        return {"csrf_token": session["_csrf"], "unread": unread}

    def login_required(*roles):
        def deco(view):
            @functools.wraps(view)
            def wrapped(*a, **kw):
                if g.user is None:
                    return redirect(url_for("login"))
                if roles and g.user["role"] not in roles:
                    abort(403)
                return view(*a, **kw)
            return wrapped
        return deco

    def can_view(issue):
        u = g.user
        if u["role"] == "student":
            return issue["student_id"] == u["id"]
        if u["role"] == "admin":
            return True
        return issue["department"] == u["department"]

    def add_event(issue_id, kind, message):
        db.get_db().execute(
            "INSERT INTO events (issue_id, actor_id, kind, message) VALUES (?,?,?,?)",
            (issue_id, g.user["id"], kind, message))

    def notify(user_id, issue_id, message):
        db.get_db().execute(
            "INSERT INTO notifications (user_id, issue_id, message) VALUES (?,?,?)",
            (user_id, issue_id, message))

    # ---------- auth ----------
    @app.route("/")
    def index():
        if g.user is None:
            return redirect(url_for("login"))
        return redirect(url_for("student_home" if g.user["role"] == "student" else "official_home"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            pw = request.form.get("password", "")
            error = None
            if len(name) < 2:
                error = "Please enter your name."
            elif not EMAIL_RE.match(email):
                error = "Please enter a valid email."
            elif len(pw) < 8:
                error = "Password must be at least 8 characters."
            elif db.get_db().execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
                error = "An account with this email already exists."
            if error:
                flash(error, "error")
            else:
                db.get_db().execute(
                    "INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?, 'student')",
                    (name, email, generate_password_hash(pw)))
                db.get_db().commit()
                flash("Account created. Please log in.", "ok")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            user = db.get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("index"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---------- student ----------
    @app.route("/student")
    @login_required("student")
    def student_home():
        conn = db.get_db()
        issues = conn.execute(
            "SELECT * FROM issues WHERE student_id=? ORDER BY created_at DESC, id DESC",
            (g.user["id"],)).fetchall()
        notes = conn.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (g.user["id"],)).fetchall()
        conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (g.user["id"],))
        conn.commit()
        return render_template("student_home.html", issues=issues, notes=notes)

    @app.route("/api/suggest", methods=["POST"])
    @login_required("student")
    def api_suggest():
        text = (request.get_json(silent=True) or {}).get("text", "")
        if len(text.strip()) < 15:
            return jsonify({"ready": False})
        r = ai.analyze(text)
        r["ready"] = True
        return jsonify(r)

    @app.route("/submit", methods=["GET", "POST"])
    @login_required("student")
    def submit():
        form = {"title": "", "description": "", "confidential": False}
        if request.method == "POST":
            form = {"title": request.form.get("title", "").strip(),
                    "description": request.form.get("description", "").strip(),
                    "confidential": request.form.get("confidential") == "on"}
            error = None
            if not 5 <= len(form["title"]) <= 120:
                error = "Title must be 5 to 120 characters."
            elif not 20 <= len(form["description"]) <= 2000:
                error = "Description must be 20 to 2000 characters."
            if error:
                flash(error, "error")
                return render_template("submit.html", form=form, dups=[])
            text = f"{form['title']}. {form['description']}"
            conn = db.get_db()
            if not request.form.get("confirm"):
                rows = conn.execute(
                    f"SELECT id,title,description FROM issues WHERE status IN "
                    f"({','.join('?' * len(OPEN_STATUSES))}) AND (confidential=0 OR student_id=?)",
                    (*OPEN_STATUSES, g.user["id"])).fetchall()
                dups = ai.find_duplicates(text, [(r["id"], r["title"], r["description"]) for r in rows])
                if dups:
                    status = {r["id"]: r for r in conn.execute(
                        "SELECT id,status FROM issues WHERE id IN (%s)" % ",".join("?" * len(dups)),
                        [d["id"] for d in dups]).fetchall()}
                    for d in dups:
                        d["status"] = status[d["id"]]["status"]
                    return render_template("submit.html", form=form, dups=dups)
            a = ai.analyze(text)
            confidential = form["confidential"] or a["sensitive"]
            review = 1  # every new issue is reviewed by a human
            cur = conn.execute(
                """INSERT INTO issues (student_id,title,description,department,priority,confidential,
                   ai_department,ai_priority,ai_confidence,ai_summary,needs_human_review)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (g.user["id"], form["title"], form["description"], a["department"], a["priority"],
                 int(confidential), a["department"], a["priority"], a["confidence"], a["summary"], review))
            iid = cur.lastrowid
            add_event(iid, "submitted", "Issue submitted by student. AI suggested "
                      f"{a['department']} / {a['priority']} priority (pending human review).")
            conn.commit()
            flash(f"Issue #{iid} submitted. You will be notified when an official updates it.", "ok")
            return redirect(url_for("issue_detail", issue_id=iid))
        return render_template("submit.html", form=form, dups=[])

    # ---------- shared detail ----------
    @app.route("/issue/<int:issue_id>")
    @login_required()
    def issue_detail(issue_id):
        conn = db.get_db()
        issue = conn.execute(
            "SELECT i.*, u.name AS student_name FROM issues i JOIN users u ON u.id=i.student_id WHERE i.id=?",
            (issue_id,)).fetchone()
        if issue is None or not can_view(issue):
            abort(404)  # do not reveal whether the issue exists
        events = conn.execute(
            "SELECT e.*, u.name AS actor, u.role AS actor_role FROM events e "
            "LEFT JOIN users u ON u.id=e.actor_id WHERE issue_id=? ORDER BY e.id", (issue_id,)).fetchall()
        hide_name = issue["confidential"] and g.user["role"] == "official"
        return render_template("issue_detail.html", issue=issue, events=events, hide_name=hide_name,
                               departments=ai.DEPARTMENTS, priorities=PRIORITIES, statuses=STATUSES)

    # ---------- officials ----------
    @app.route("/official")
    @login_required("official", "admin")
    def official_home():
        conn = db.get_db()
        u = g.user
        where, params = [], []
        if u["role"] == "official":
            where.append("department = ?")
            params.append(u["department"])
        elif request.args.get("department") in ai.DEPARTMENTS:
            where.append("department = ?")
            params.append(request.args["department"])
        for key, allowed in (("status", STATUSES), ("priority", PRIORITIES)):
            if request.args.get(key) in allowed:
                where.append(f"{key} = ?")
                params.append(request.args[key])
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        issues = conn.execute(
            f"SELECT * FROM issues {clause} ORDER BY "
            "CASE status WHEN 'resolved' THEN 2 WHEN 'closed' THEN 2 ELSE 1 END, "
            "CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, created_at",
            params).fetchall()

        scope = "WHERE department = ?" if u["role"] == "official" else ""
        sp = [u["department"]] if u["role"] == "official" else []

        def counts(col):
            return conn.execute(f"SELECT {col} AS k, COUNT(*) AS n FROM issues {scope} GROUP BY {col}", sp).fetchall()

        today = date.today().isoformat()
        overdue = conn.execute(
            f"SELECT COUNT(*) FROM issues {scope + ' AND' if scope else 'WHERE'} deadline IS NOT NULL "
            f"AND deadline < ? AND status IN ('submitted','under_review','in_progress','needs_info')",
            (*sp, today)).fetchone()[0]
        awaiting = conn.execute(
            f"SELECT COUNT(*) FROM issues {scope + ' AND' if scope else 'WHERE'} needs_human_review=1", sp
        ).fetchone()[0]
        stats = {"by_status": counts("status"), "by_priority": counts("priority"),
                 "by_department": counts("department") if u["role"] == "admin" else [],
                 "overdue": overdue, "awaiting_review": awaiting, "total": len(issues)}
        return render_template("official_home.html", issues=issues, stats=stats, today=today,
                               departments=ai.DEPARTMENTS, priorities=PRIORITIES, statuses=STATUSES)

    @app.route("/issue/<int:issue_id>/update", methods=["POST"])
    @login_required("official", "admin")
    def update_issue(issue_id):
        conn = db.get_db()
        issue = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
        if issue is None or not can_view(issue):
            abort(404)
        dept = request.form.get("department", issue["department"])
        prio = request.form.get("priority", issue["priority"])
        status = request.form.get("status", issue["status"])
        message = request.form.get("message", "").strip()[:1000]
        deadline = request.form.get("deadline", "").strip() or None
        if dept not in ai.DEPARTMENTS or prio not in PRIORITIES or status not in STATUSES:
            abort(400)
        if deadline:
            try:
                datetime.strptime(deadline, "%Y-%m-%d")
            except ValueError:
                flash("Deadline must be a valid date.", "error")
                return redirect(url_for("issue_detail", issue_id=issue_id))
        if status == "closed" and not message:
            flash("Closing an issue needs a written explanation for the student.", "error")
            return redirect(url_for("issue_detail", issue_id=issue_id))

        if dept != issue["department"]:
            add_event(issue_id, "assign", f"Reassigned from {issue['department']} to {dept}")
        if prio != issue["priority"]:
            add_event(issue_id, "priority", f"Priority changed from {issue['priority']} to {prio}")
        if status != issue["status"]:
            add_event(issue_id, "status", f"Status changed to {status.replace('_', ' ')}")
            notify(issue["student_id"], issue_id,
                   f"Issue #{issue_id} is now '{status.replace('_', ' ')}'.")
        if message:
            add_event(issue_id, "response", message)
            notify(issue["student_id"], issue_id, f"New response on issue #{issue_id}.")
        conn.execute(
            "UPDATE issues SET department=?, priority=?, status=?, deadline=?, needs_human_review=0, "
            "updated_at=datetime('now') WHERE id=?", (dept, prio, status, deadline, issue_id))
        conn.commit()
        flash("Issue updated.", "ok")
        return redirect(url_for("issue_detail", issue_id=issue_id))

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, msg="You do not have access to this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, msg="Page not found."), 404

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request")), 400

    return app


if __name__ == "__main__":
    create_app().run(debug=os.getenv("FLASK_DEBUG") == "1")
