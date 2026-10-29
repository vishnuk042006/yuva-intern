"""Small calculator demonstrating functions, error handling and docstrings."""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


OPERATIONS = {"+": add, "-": subtract, "*": multiply, "/": divide}


def calculate(a: float, op: str, b: float) -> float:
    if op not in OPERATIONS:
        raise ValueError(f"Unsupported operator: {op}")
    return OPERATIONS[op](a, b)


if __name__ == "__main__":
    try:
        x = float(input("First number: "))
        op = input("Operator (+ - * /): ").strip()
        y = float(input("Second number: "))
        print("Result:", calculate(x, op, y))
    except ValueError as err:
        print("Error:", err)
