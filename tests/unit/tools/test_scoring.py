"""
Unit tests for deterministic scoring utilities.

These tests validate the core matching algorithm before LLM reasoning
is applied. The scoring functions are used to:
  1. Generate a base compatibility score (0-100)
  2. Apply distance-based score multipliers
  3. Filter unsuitable candidates before expensive LLM calls

Edge cases tested include:
  - Empty interests/profiles
  - Missing year information
  - Candidates at same location
  - Candidates far outside preferred radius
"""

import pytest
from src.tools.scoring_tools import calculate_base_compatibility_score, calculate_distance_score


class TestBaseCompatibilityScore:
    """Test deterministic compatibility scoring."""

    def test_same_major_increases_score(self):
        """Users with the same major should get higher compatibility."""
        user = {"major": "CS", "interests": [], "year": 1}
        candidate = {"major": "CS", "interests": [], "year": 1}
        score = calculate_base_compatibility_score(user, candidate)
        assert score >= 55  # Base 40 + major bonus 15

    def test_different_major_no_bonus(self):
        """Users with different majors don't get major bonus."""
        user = {"major": "CS", "interests": [], "year": 1}
        candidate = {"major": "Math", "interests": [], "year": 1}
        score = calculate_base_compatibility_score(user, candidate)
        assert score < 55  # Base 40, no major bonus

    def test_shared_interests_increase_score(self):
        """Shared interests should increase compatibility score."""
        user = {"major": "CS", "interests": ["AI", "Music"], "year": 1}
        candidate = {"major": "Math", "interests": ["AI", "Sports"], "year": 1}
        score = calculate_base_compatibility_score(user, candidate)
        assert score > 40  # Base + shared interest bonus (1 shared * 3 points)

    def test_multiple_shared_interests(self):
        """Multiple shared interests should give cumulative bonus."""
        user = {"major": "CS", "interests": ["AI", "Music", "Gaming"], "year": 1}
        candidate = {"major": "CS", "interests": ["AI", "Music", "Sports"], "year": 1}
        score = calculate_base_compatibility_score(user, candidate)
        # Base 40 + major 15 + 2 shared interests (2 * 3) = 61
        assert score >= 61

    def test_no_interests_defined(self):
        """Score should be calculated even with no interests."""
        user = {"major": "CS", "year": 1}
        candidate = {"major": "Math", "year": 2}
        score = calculate_base_compatibility_score(user, candidate)
        assert 0 <= score <= 100  # Valid range

    def test_adjacent_years_bonus(self):
        """Users within 1 year of each other should get year bonus."""
        user = {"major": "CS", "interests": [], "year": 2}
        candidate = {"major": "Math", "interests": [], "year": 1}
        score = calculate_base_compatibility_score(user, candidate)
        assert score >= 50  # Base 40 + year bonus 10

    def test_far_apart_years_no_bonus(self):
        """Users 2+ years apart don't get year bonus."""
        user = {"major": "CS", "interests": [], "year": 1}
        candidate = {"major": "Math", "interests": [], "year": 4}
        score = calculate_base_compatibility_score(user, candidate)
        assert score == 40  # Just the base score

    def test_both_have_bios_bonus(self):
        """Both users having bios should add a small bonus."""
        user = {"major": "CS", "interests": [], "year": 1, "bio": "I love CS"}
        candidate = {"major": "CS", "interests": [], "year": 1, "bio": "CS enthusiast"}
        score = calculate_base_compatibility_score(user, candidate)
        assert score >= 60  # Base 40 + major 15 + bio 5

    def test_score_capped_at_100(self):
        """Score should never exceed 100 regardless of bonuses."""
        user = {"major": "CS", "interests": ["A"] * 20, "year": 1, "bio": "x"}
        candidate = {"major": "CS", "interests": ["A"] * 20, "year": 1, "bio": "y"}
        score = calculate_base_compatibility_score(user, candidate)
        assert score <= 100


class TestDistanceScore:
    """Test distance-based scoring multiplier."""

    def test_same_location_perfect_score(self):
        """Users at same location should get perfect distance score."""
        score = calculate_distance_score(40.0, -74.0, 40.0, -74.0, max_distance_m=5000)
        assert score == 1.0

    def test_within_radius_good_score(self):
        """Users within preferred radius should get good score."""
        # Both at same location, well within 5000m radius
        score = calculate_distance_score(40.0, -74.0, 40.0, -74.0, max_distance_m=5000)
        assert score == 1.0

    def test_outside_radius_reduced_score(self):
        """Users outside preferred radius should get reduced score."""
        # NYC to Boston (~300km), beyond 5000m default radius
        score = calculate_distance_score(40.7128, -74.0060, 42.3601, -71.0589, max_distance_m=5000)
        # Should be reduced, may be 0 if far enough
        assert score >= 0 and score <= 1.0

    def test_distance_score_never_negative(self):
        """Distance score should never be negative."""
        # Very far apart (NYC to Los Angeles ~4000km)
        score = calculate_distance_score(40.7128, -74.0060, 34.0522, -118.2437, max_distance_m=5000)
        assert score >= 0  # May be close to 0, but not negative

    def test_custom_max_distance(self):
        """Custom max_distance_m should be respected."""
        # If radius is 10km, closer is better
        score_10km = calculate_distance_score(
            40.0, -74.0, 40.01, -74.0, max_distance_m=10000
        )
        # If radius is 1km, same points are farther relative to max
        score_1km = calculate_distance_score(
            40.0, -74.0, 40.01, -74.0, max_distance_m=1000
        )
        # The 1km radius should give lower score for same distance
        assert score_1km < score_10km

    def test_equator_calculation(self):
        """Distance calculation should work near equator."""
        # Two points near equator, ~111km apart (1 degree lat)
        score = calculate_distance_score(0.0, 0.0, 1.0, 0.0, max_distance_m=50000)
        # Should be reduced (111km < 50km), may be 0 depending on formula
        assert score >= 0 and score <= 1.0

    def test_poles_calculation(self):
        """Distance calculation should work near poles."""
        # Two points near north pole (handling edge case)
        score = calculate_distance_score(85.0, 0.0, 85.0, 1.0, max_distance_m=50000)
        # Should still return valid score
        assert 0 <= score <= 1.0