import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from calculator import calculate, divide
from todo import add_task, complete_task


def test_basic_operations():
    assert calculate(2, "+", 3) == 5
    assert calculate(6, "*", 7) == 42
    assert calculate(9, "-", 4) == 5
    assert calculate(8, "/", 2) == 4


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(1, 0)


def test_bad_operator():
    with pytest.raises(ValueError):
        calculate(1, "^", 2)


def test_todo_flow():
    tasks = []
    add_task(tasks, "learn git")
    complete_task(tasks, 0)
    assert tasks[0] == {"title": "learn git", "done": True}
