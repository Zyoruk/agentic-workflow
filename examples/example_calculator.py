"""Simple calculator module for testing demonstration."""

from typing import List


def add(a: float, b: float) -> float:
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b


def divide(dividend: float, divisor: float) -> float:
    """Divide two numbers.

    Args:
        dividend: Number to be divided
        divisor: Number to divide by

    Returns:
        Result of division

    Raises:
        ValueError: If divisor is zero
    """
    if divisor == 0:
        raise ValueError("Cannot divide by zero")
    return dividend / divisor


def factorial(n: int) -> int:
    """Calculate factorial of a number.

    Args:
        n: Non-negative integer

    Returns:
        Factorial of n

    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)


class Statistics:
    """Simple statistics calculator."""

    def __init__(self):
        """Initialize statistics calculator."""
        self.data = []

    def add_data(self, value: float) -> None:
        """Add a value to the dataset.

        Args:
            value: Value to add
        """
        self.data.append(value)

    def get_mean(self) -> float:
        """Calculate mean of the dataset.

        Returns:
            Mean value

        Raises:
            ValueError: If dataset is empty
        """
        if not self.data:
            raise ValueError("Cannot calculate mean of empty dataset")
        return sum(self.data) / len(self.data)

    def get_median(self) -> float:
        """Calculate median of the dataset.

        Returns:
            Median value

        Raises:
            ValueError: If dataset is empty
        """
        if not self.data:
            raise ValueError("Cannot calculate median of empty dataset")

        sorted_data = sorted(self.data)
        n = len(sorted_data)

        if n % 2 == 0:
            return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
        else:
            return sorted_data[n // 2]

    def clear(self) -> None:
        """Clear all data from the dataset."""
        self.data.clear()
