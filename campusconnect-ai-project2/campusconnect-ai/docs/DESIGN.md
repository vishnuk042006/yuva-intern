# Design Document

## 1. Problem
Student voice gets lost; students do not know whom to approach; issues pass through
intermediaries; there is no status tracking; repeat submissions waste time; urgent and
sensitive issues are buried.

## 2. Users
Students, department officers (HODs, hostel warden, transport, library, etc.), and the
Principal/admin.

## 3. Workflow
Student submits -> AI analyses (department, priority, sensitivity, summary, duplicates)
-> official reviews and can override -> action and status update -> student notified.

Statuses: submitted, under review, in progress, needs info, resolved, closed.
There is intentionally no "rejected" status; closing needs a written explanation.

## 4. Architecture
| Module | Responsibility |
|--------|----------------|
| `app.py` | Routes, access control, validation, CSRF, workflow |
| `ai.py` | NLP suggestions (no database access, easy to test) |
| `db.py` | SQLite connection and schema |
| `templates/`, `static/` | HTML (Jinja2) and CSS |
| `data/training_data.py` | Labelled examples for routing |
| `seed.py` | Demo data |

## 5. Database
users(id, name, email, password_hash, role, department)
issues(id, student_id, title, description, department, priority, status, confidential,
       ai_department, ai_priority, ai_confidence, ai_summary, needs_human_review, deadline, ...)
events(id, issue_id, actor_id, kind, message, created_at)   -- full audit timeline
notifications(id, user_id, issue_id, message, is_read, created_at)
AI suggestions are stored next to the human-confirmed values so accuracy can be measured later.

## 6. Security decisions
- Passwords hashed (werkzeug); parameterised SQL; Jinja auto-escaping (XSS)
- CSRF token on every POST; HttpOnly + SameSite cookies
- Role checks on every route; unauthorised issue access returns 404 (does not reveal existence)
- Input length validation; secrets come from environment variables

## 7. Testing
18 automated tests: AI behaviour, auth, CSRF, validation, duplicate flow, access control,
department isolation, update history and notifications, closing rule, confidentiality.

## 8. Limitations and future work
- Training set is small; more real examples will improve routing accuracy
- Duplicate detection uses TF-IDF; Sentence Transformers would understand meaning better
- Add appointment scheduling, email/SMS notifications, a guided chatbot, and PostgreSQL
- Set `SECRET_KEY` and use HTTPS (e.g. gunicorn behind Nginx) for real deployment
