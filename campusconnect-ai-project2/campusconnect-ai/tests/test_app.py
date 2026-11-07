import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from werkzeug.security import generate_password_hash

import ai
import db
from app import create_app


@pytest.fixture
def app(tmp_path):
    app = create_app({"DATABASE": str(tmp_path / "t.db"), "TESTING": True})
    with app.app_context():
        c = db.get_db()
        for name, email, role, dept in [("Admin", "admin@x.edu", "admin", None),
                                        ("Hostel Off", "hostel@x.edu", "official", "Hostel"),
                                        ("Lib Off", "lib@x.edu", "official", "Library")]:
            c.execute("INSERT INTO users (name,email,password_hash,role,department) VALUES (?,?,?,?,?)",
                      (name, email, generate_password_hash("password123"), role, dept))
        c.commit()
    return app


def token(client, path="/login"):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)


def register_login(client, email="stu@x.edu", name="Stu"):
    client.post("/register", data={"_csrf": token(client, "/register"), "name": name, "email": email,
                                   "password": "password123"})
    return login(client, email)


def login(client, email, pw="password123"):
    return client.post("/login", data={"_csrf": token(client), "email": email, "password": pw},
                       follow_redirects=True)


def submit(client, title, desc, **extra):
    data = {"_csrf": token(client, "/submit"), "title": title, "description": desc, **extra}
    return client.post("/submit", data=data, follow_redirects=True)


# ---- AI layer ----
def test_routing_examples():
    assert ai.classify("No hot water in the hostel bathrooms for a week")[0] == "Hostel"
    assert ai.classify("The college bus is late every morning")[0] == "Transport"
    assert ai.classify("My revaluation result is delayed")[0] == "Examination"


def test_unclear_text_goes_to_administration():
    assert ai.classify("I like pizza very much")[0] == "Administration"


def test_sensitive_is_high_priority():
    priority, sensitive = ai.prioritize("A senior is harassing me")
    assert priority == "high" and sensitive


def test_duplicate_detection():
    cands = [(1, "Wifi slow", "campus wifi very slow in CSE block"), (2, "Bus late", "route 5 bus is late")]
    hits = ai.find_duplicates("The campus wifi is very slow in the CSE block", cands)
    assert hits and hits[0]["id"] == 1


def test_summary_is_short():
    assert len(ai.summarize("word " * 200)) <= 200


# ---- auth and security ----
def test_register_and_login(app):
    c = app.test_client()
    r = register_login(c)
    assert b"My issues" in r.data


def test_wrong_password(app):
    c = app.test_client()
    r = login(c, "nobody@x.edu", "wrongpass")
    assert b"Invalid email or password" in r.data


def test_csrf_required(app):
    c = app.test_client()
    assert c.post("/login", data={"email": "a@b.c", "password": "x"}).status_code == 400


def test_short_password_rejected(app):
    c = app.test_client()
    r = c.post("/register", data={"_csrf": token(c, "/register"), "name": "A B", "email": "a@b.co",
                                  "password": "short"}, follow_redirects=True)
    assert b"at least 8" in r.data


def test_student_cannot_open_official_dashboard(app):
    c = app.test_client()
    register_login(c)
    assert c.get("/official").status_code == 403


# ---- workflow ----
def test_submit_routes_to_department(app):
    c = app.test_client()
    register_login(c)
    r = submit(c, "No hot water", "There is no hot water in the hostel bathrooms for one week now.")
    assert b"submitted" in r.data
    with app.app_context():
        row = db.get_db().execute("SELECT * FROM issues").fetchone()
    assert row["department"] == "Hostel" and row["needs_human_review"] == 1


def test_validation_on_submit(app):
    c = app.test_client()
    register_login(c)
    assert b"Title must be" in submit(c, "hi", "x" * 30).data
    assert b"Description must be" in submit(c, "Valid title", "too short").data


def test_duplicate_warning_then_confirm(app):
    c = app.test_client()
    register_login(c)
    t, d = "Wifi slow in CSE block", "The campus wifi in the CSE block is very slow and keeps disconnecting."
    submit(c, t, d)
    r = submit(c, t, d)
    assert b"Similar issues already exist" in r.data
    r = submit(c, t, d, confirm="1")
    with app.app_context():
        assert db.get_db().execute("SELECT COUNT(*) FROM issues").fetchone()[0] == 2


def test_students_cannot_see_each_others_issues(app):
    a, b = app.test_client(), app.test_client()
    register_login(a, "a@x.edu", "Aaa")
    submit(a, "Library books missing", "The reference books for my course are not in the library at all.")
    register_login(b, "b@x.edu", "Bbb")
    assert b.get("/issue/1").status_code == 404


def test_official_sees_only_own_department(app):
    s = app.test_client()
    register_login(s)
    submit(s, "No hot water", "There is no hot water in the hostel bathrooms for one week now.")
    lib, hostel = app.test_client(), app.test_client()
    login(lib, "lib@x.edu")
    login(hostel, "hostel@x.edu")
    assert lib.get("/issue/1").status_code == 404
    assert hostel.get("/issue/1").status_code == 200


def test_update_creates_history_and_notification(app):
    s, o = app.test_client(), app.test_client()
    register_login(s)
    submit(s, "No hot water", "There is no hot water in the hostel bathrooms for one week now.")
    login(o, "hostel@x.edu")
    r = o.post("/issue/1/update", data={"_csrf": token(o, "/official"), "department": "Hostel",
               "priority": "high", "status": "in_progress", "message": "Plumber assigned.",
               "deadline": "2030-01-01"}, follow_redirects=True)
    assert b"Issue updated" in r.data
    with app.app_context():
        c = db.get_db()
        assert c.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 2
        assert c.execute("SELECT needs_human_review FROM issues").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM events WHERE kind='response'").fetchone()[0] == 1
    assert b"in progress" in s.get("/student").data


def test_closing_requires_explanation(app):
    s, o = app.test_client(), app.test_client()
    register_login(s)
    submit(s, "No hot water", "There is no hot water in the hostel bathrooms for one week now.")
    login(o, "hostel@x.edu")
    r = o.post("/issue/1/update", data={"_csrf": token(o, "/official"), "department": "Hostel",
               "priority": "low", "status": "closed", "message": ""}, follow_redirects=True)
    assert b"needs a written explanation" in r.data
    with app.app_context():
        assert db.get_db().execute("SELECT status FROM issues").fetchone()[0] == "submitted"


def test_confidential_hides_name_from_officer_not_admin(app):
    s, o, a = app.test_client(), app.test_client(), app.test_client()
    register_login(s, "secret@x.edu", "Secret Student")
    submit(s, "Harassment report", "A senior student keeps harassing me near the hostel.")
    login(o, "hostel@x.edu")
    login(a, "admin@x.edu")
    with app.app_context():
        dept = db.get_db().execute("SELECT department FROM issues").fetchone()[0]
    assert dept == "Student Welfare"   # routed by AI; hostel officer cannot even see it
    assert o.get("/issue/1").status_code == 404
    assert b"Secret Student" in a.get("/issue/1").data
