"""Number guessing game demonstrating loops, conditions and the random module."""
import random


def play(low: int = 1, high: int = 20, max_tries: int = 5) -> bool:
    secret = random.randint(low, high)
    for attempt in range(1, max_tries + 1):
        try:
            guess = int(input(f"Attempt {attempt}/{max_tries} - guess {low}-{high}: "))
        except ValueError:
            print("Please enter a whole number.")
            continue
        if guess == secret:
            print("Correct!")
            return True
        print("Too low." if guess < secret else "Too high.")
    print(f"Out of tries. The number was {secret}.")
    return False


if __name__ == "__main__":
    play()
