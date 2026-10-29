"""Business layer: validation rules and queries. No printing, no argument parsing."""
import csv
from datetime import date, datetime


class ValidationError(ValueError):
    """Raised when user input breaks a business rule."""


def _parse_date(value):
    if value is None:
        return date.today().isoformat()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        raise ValidationError("Date must be in YYYY-MM-DD format")


def add_expense(conn, amount, category, note="", spent_on=None):
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValidationError("Amount must be a number")
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero")
    category = (category or "").strip().lower()
    if not category:
        raise ValidationError("Category is required")
    cur = conn.execute(
        "INSERT INTO expenses (amount, category, note, spent_on) VALUES (?, ?, ?, ?)",
        (amount, category, note.strip(), _parse_date(spent_on)),
    )
    conn.commit()
    return cur.lastrowid


def list_expenses(conn, category=None, month=None):
    """Return expenses, optionally filtered by category and/or month (YYYY-MM)."""
    sql, params = "SELECT * FROM expenses WHERE 1=1", []
    if category:
        sql += " AND category = ?"
        params.append(category.strip().lower())
    if month:
        sql += " AND substr(spent_on, 1, 7) = ?"
        params.append(month)
    sql += " ORDER BY spent_on DESC, id DESC"
    return conn.execute(sql, params).fetchall()


def delete_expense(conn, expense_id):
    cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    if cur.rowcount == 0:
        raise ValidationError(f"No expense with id {expense_id}")


def summary_by_category(conn, month=None):
    sql = "SELECT category, ROUND(SUM(amount), 2) AS total, COUNT(*) AS count FROM expenses"
    params = []
    if month:
        sql += " WHERE substr(spent_on, 1, 7) = ?"
        params.append(month)
    sql += " GROUP BY category ORDER BY total DESC"
    return conn.execute(sql, params).fetchall()


def export_csv(conn, path):
    rows = list_expenses(conn)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "amount", "category", "note", "spent_on"])
        for r in rows:
            w.writerow([r["id"], r["amount"], r["category"], r["note"], r["spent_on"]])
    return len(rows)
