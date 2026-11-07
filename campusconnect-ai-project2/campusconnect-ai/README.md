# CampusConnect AI

A paperless student issue platform. Students report problems, AI suggests the right
department and priority, authorised officials review and act, and students are notified
and can track status. **AI only assists. Officials decide.**

Stack: Python, Flask, SQLite, HTML/CSS, scikit-learn (NLP).

## Run in VS Code
    python -m venv .venv
    .venv\Scripts\activate          (Windows)   |   source .venv/bin/activate  (Mac/Linux)
    pip install -r requirements.txt
    python seed.py                   # demo accounts + sample issues
    python app.py                    # open http://127.0.0.1:5000

Demo logins (password `demo12345`): `student@campus.edu`, `principal@campus.edu` (sees all),
`hostel@campus.edu`, `itnetwork@campus.edu`, and one officer per department.

## Tests
    pytest

## Features
- Student: register/login, report issue, confidential option, live AI suggestion, duplicate warning,
  status tracking with timeline, notifications
- Official: department dashboard, filters, analytics (status, priority, overdue, awaiting review),
  confirm/override AI routing and priority, reassign, respond, set deadline, update status
- Admin (Principal): sees every department and the department breakdown

## AI features (ai.py)
| Feature | Method |
|---------|--------|
| Department routing | TF-IDF + Logistic Regression trained on `data/training_data.py` |
| Low-confidence cases | Sent to "Administration" for human routing |
| Priority and sensitive-case flag | Keyword rules (explainable) |
| Duplicate detection | TF-IDF cosine similarity against open issues |
| Summary | Extractive: picks the most informative sentence |

## Responsible AI
- Every issue is reviewed by a human; AI output is shown as a suggestion
- No automatic rejection; closing an issue requires a written explanation to the student
- Sensitive topics (harassment, ragging, mental health) are marked confidential and high priority
- Confidential issues hide the student's name from department officers

See `docs/DESIGN.md` for architecture, database schema and decisions.
