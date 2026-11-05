import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from expense_tracker import database, service
from expense_tracker.cli import main


@pytest.fixture
def conn():
    c = database.connect(":memory:")
    yield c
    c.close()


def test_add_and_list(conn):
    service.add_expense(conn, "12.5", "Food", "lunch", "2026-10-01")
    rows = service.list_expenses(conn)
    assert len(rows) == 1 and rows[0]["category"] == "food" and rows[0]["amount"] == 12.5


@pytest.mark.parametrize("amount", ["abc", "0", "-5", None])
def test_invalid_amount(conn, amount):
    with pytest.raises(service.ValidationError):
        service.add_expense(conn, amount, "food")


def test_empty_category(conn):
    with pytest.raises(service.ValidationError):
        service.add_expense(conn, 5, "   ")


def test_bad_date(conn):
    with pytest.raises(service.ValidationError):
        service.add_expense(conn, 5, "food", spent_on="01-10-2026")


def test_filters(conn):
    service.add_expense(conn, 10, "food", spent_on="2026-09-10")
    service.add_expense(conn, 20, "travel", spent_on="2026-10-02")
    assert len(service.list_expenses(conn, category="FOOD")) == 1
    assert len(service.list_expenses(conn, month="2026-10")) == 1


def test_summary(conn):
    service.add_expense(conn, 10, "food", spent_on="2026-10-01")
    service.add_expense(conn, 15, "food", spent_on="2026-10-02")
    service.add_expense(conn, 5, "books", spent_on="2026-10-03")
    s = {r["category"]: r["total"] for r in service.summary_by_category(conn)}
    assert s == {"food": 25.0, "books": 5.0}


def test_delete(conn):
    i = service.add_expense(conn, 10, "food")
    service.delete_expense(conn, i)
    assert service.list_expenses(conn) == []
    with pytest.raises(service.ValidationError):
        service.delete_expense(conn, i)


def test_export_csv(conn, tmp_path):
    service.add_expense(conn, 10, "food", "tea", "2026-10-01")
    out = tmp_path / "out.csv"
    assert service.export_csv(conn, str(out)) == 1
    assert list(csv.reader(open(out)))[1][2] == "food"


def test_cli_end_to_end(tmp_path, capsys):
    db = str(tmp_path / "t.db")
    assert main(["--db", db, "add", "42", "food", "--date", "2026-10-05"]) == 0
    assert main(["--db", db, "summary"]) == 0
    assert "42.00" in capsys.readouterr().out
    assert main(["--db", db, "add", "-1", "food"]) == 1
