# Generated tests for example_calculator.py
import pytest
from example_calculator import add, divide, factorial, Statistics


class TestCalculatorFunctions:
    """Test cases for calculator functions."""

    def test_add_basic(self):
        """Test basic addition functionality."""
        assert add(2, 3) == 5
        assert add(-1, 1) == 0
        assert add(0, 0) == 0

    def test_add_edge_cases(self):
        """Test edge cases for addition."""
        assert add(1.5, 2.5) == 4.0
        assert add(-5, -3) == -8
        assert add(1000000, 1000000) == 2000000

    def test_divide_basic(self):
        """Test basic division functionality."""
        assert divide(10, 2) == 5.0
        assert divide(9, 3) == 3.0
        assert divide(1, 1) == 1.0

    def test_divide_edge_cases(self):
        """Test edge cases for division."""
        assert divide(7, 2) == 3.5
        assert divide(-10, 2) == -5.0
        assert divide(10, -2) == -5.0

    def test_divide_error_handling(self):
        """Test error handling for division."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(-5, 0)

    def test_factorial_basic(self):
        """Test basic factorial functionality."""
        assert factorial(0) == 1
        assert factorial(1) == 1
        assert factorial(5) == 120
        assert factorial(3) == 6

    def test_factorial_edge_cases(self):
        """Test edge cases for factorial."""
        assert factorial(10) == 3628800

    def test_factorial_error_handling(self):
        """Test error handling for factorial."""
        with pytest.raises(ValueError, match="Factorial is not defined for negative numbers"):
            factorial(-1)

        with pytest.raises(ValueError, match="Factorial is not defined for negative numbers"):
            factorial(-5)


class TestStatistics:
    """Test cases for Statistics class."""

    @pytest.fixture
    def stats(self):
        """Create statistics instance for testing."""
        return Statistics()

    def test_add_data(self, stats):
        """Test adding data to statistics."""
        stats.add_data(5.0)
        assert len(stats.data) == 1
        assert stats.data[0] == 5.0

        stats.add_data(10.0)
        assert len(stats.data) == 2

    def test_get_mean_basic(self, stats):
        """Test basic mean calculation."""
        stats.add_data(2.0)
        stats.add_data(4.0)
        stats.add_data(6.0)
        assert stats.get_mean() == 4.0

    def test_get_mean_single_value(self, stats):
        """Test mean calculation with single value."""
        stats.add_data(7.5)
        assert stats.get_mean() == 7.5

    def test_get_mean_error_handling(self, stats):
        """Test error handling for mean calculation."""
        with pytest.raises(ValueError, match="Cannot calculate mean of empty dataset"):
            stats.get_mean()

    def test_get_median_odd_count(self, stats):
        """Test median calculation with odd number of values."""
        for value in [1, 3, 5, 7, 9]:
            stats.add_data(value)
        assert stats.get_median() == 5

    def test_get_median_even_count(self, stats):
        """Test median calculation with even number of values."""
        for value in [2, 4, 6, 8]:
            stats.add_data(value)
        assert stats.get_median() == 5.0

    def test_get_median_single_value(self, stats):
        """Test median calculation with single value."""
        stats.add_data(42.0)
        assert stats.get_median() == 42.0

    def test_get_median_error_handling(self, stats):
        """Test error handling for median calculation."""
        with pytest.raises(ValueError, match="Cannot calculate median of empty dataset"):
            stats.get_median()

    def test_clear(self, stats):
        """Test clearing data from statistics."""
        stats.add_data(1.0)
        stats.add_data(2.0)
        assert len(stats.data) == 2

        stats.clear()
        assert len(stats.data) == 0

    def test_workflow_integration(self, stats):
        """Test complete workflow with statistics."""
        # Add sample data
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in data:
            stats.add_data(value)

        # Test calculations
        assert stats.get_mean() == 3.0
        assert stats.get_median() == 3.0
        assert len(stats.data) == 5

        # Clear and verify
        stats.clear()
        assert len(stats.data) == 0
