"""Create demo accounts and a few sample issues:  python seed.py"""
from werkzeug.security import generate_password_hash

import ai
import db
from app import create_app

DEMO_PASSWORD = "demo12345"   # demo only - change for real use

app = create_app()
with app.app_context():
    conn = db.get_db()
    users = [("Principal", "principal@campus.edu", "admin", None),
             ("Demo Student", "student@campus.edu", "student", None)]
    for dept in ai.DEPARTMENTS:
        slug = dept.lower().replace(" & ", "").replace(" ", "")
        users.append((f"{dept} Officer", f"{slug}@campus.edu", "official", dept))
    for name, email, role, dept in users:
        conn.execute("INSERT OR IGNORE INTO users (name,email,password_hash,role,department) VALUES (?,?,?,?,?)",
                     (name, email, generate_password_hash(DEMO_PASSWORD), role, dept))
    conn.commit()
    student = conn.execute("SELECT id FROM users WHERE email='student@campus.edu'").fetchone()["id"]
    if conn.execute("SELECT COUNT(*) FROM issues").fetchone()[0] == 0:
        samples = [("Campus wifi very slow", "The wifi in the CSE block is extremely slow and keeps disconnecting during lab hours."),
                   ("No hot water in hostel", "There has been no hot water in the boys hostel bathrooms for a week. This is affecting everyone."),
                   ("Bus always late", "The route 5 college bus reaches the campus late almost every day and we miss the first hour.")]
        for title, desc in samples:
            a = ai.analyze(f"{title}. {desc}")
            conn.execute("""INSERT INTO issues (student_id,title,description,department,priority,ai_department,
                            ai_priority,ai_confidence,ai_summary) VALUES (?,?,?,?,?,?,?,?,?)""",
                         (student, title, desc, a["department"], a["priority"], a["department"],
                          a["priority"], a["confidence"], a["summary"]))
        conn.commit()
    print("Seeded. Login examples (password: %s):" % DEMO_PASSWORD)
    print("  student@campus.edu | principal@campus.edu | hostel@campus.edu | itnetwork@campus.edu")
