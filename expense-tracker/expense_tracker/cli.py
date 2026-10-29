"""Presentation layer: parses arguments and prints results."""
import argparse
import sys

from . import database, service


def build_parser():
    p = argparse.ArgumentParser(prog="expense-tracker", description="Track your spending.")
    p.add_argument("--db", default="expenses.db", help="database file (default: expenses.db)")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="add an expense")
    a.add_argument("amount")
    a.add_argument("category")
    a.add_argument("--note", default="")
    a.add_argument("--date", help="YYYY-MM-DD (default: today)")

    l = sub.add_parser("list", help="list expenses")
    l.add_argument("--category")
    l.add_argument("--month", help="YYYY-MM")

    d = sub.add_parser("delete", help="delete an expense by id")
    d.add_argument("id", type=int)

    s = sub.add_parser("summary", help="totals per category")
    s.add_argument("--month", help="YYYY-MM")

    e = sub.add_parser("export", help="export all expenses to CSV")
    e.add_argument("path")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    conn = database.connect(args.db)
    try:
        if args.command == "add":
            new_id = service.add_expense(conn, args.amount, args.category, args.note, args.date)
            print(f"Added expense #{new_id}")
        elif args.command == "list":
            rows = service.list_expenses(conn, args.category, args.month)
            if not rows:
                print("No expenses found.")
            for r in rows:
                print(f"#{r['id']:<3} {r['spent_on']}  {r['amount']:>9.2f}  {r['category']:<12} {r['note']}")
        elif args.command == "delete":
            service.delete_expense(conn, args.id)
            print(f"Deleted expense #{args.id}")
        elif args.command == "summary":
            rows = service.summary_by_category(conn, args.month)
            if not rows:
                print("No expenses found.")
            for r in rows:
                print(f"{r['category']:<12} {r['total']:>10.2f}  ({r['count']} items)")
            if rows:
                print(f"{'TOTAL':<12} {sum(r['total'] for r in rows):>10.2f}")
        elif args.command == "export":
            n = service.export_csv(conn, args.path)
            print(f"Exported {n} expenses to {args.path}")
    except service.ValidationError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
