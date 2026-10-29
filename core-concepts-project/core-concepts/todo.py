"""Command-line to-do list demonstrating lists, dicts, file I/O and JSON."""
import json
import sys
from pathlib import Path

DB = Path("tasks.json")


def load_tasks() -> list:
    if DB.exists():
        return json.loads(DB.read_text())
    return []


def save_tasks(tasks: list) -> None:
    DB.write_text(json.dumps(tasks, indent=2))


def add_task(tasks: list, title: str) -> None:
    tasks.append({"title": title, "done": False})


def complete_task(tasks: list, index: int) -> None:
    tasks[index]["done"] = True


def show(tasks: list) -> None:
    if not tasks:
        print("No tasks yet.")
    for i, t in enumerate(tasks):
        print(f"{i}. [{'x' if t['done'] else ' '}] {t['title']}")


def main(argv: list) -> None:
    tasks = load_tasks()
    if len(argv) >= 3 and argv[1] == "add":
        add_task(tasks, " ".join(argv[2:]))
    elif len(argv) == 3 and argv[1] == "done":
        complete_task(tasks, int(argv[2]))
    save_tasks(tasks)
    show(tasks)


if __name__ == "__main__":
    main(sys.argv)
