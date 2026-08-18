"""Tests for the constants module."""
from conflate_roads.constants import E_RATES_cellular, E_RATES_hybrid, E_RATES_tree, get_efficiency_rates


def test_efficiency_rates_have_expected_keys():
    assert set(E_RATES_tree) == {"H", "O", "S", "P", "T", "C"}
    assert set(E_RATES_cellular) == {"H", "O", "S", "P", "T", "C"}
    assert set(E_RATES_hybrid) == {"H", "O", "S", "P", "T", "C"}


def test_get_efficiency_rates_returns_selected_pattern():
    assert get_efficiency_rates("tree") is E_RATES_tree
    assert get_efficiency_rates("hybrid") is E_RATES_hybrid
    assert get_efficiency_rates("cellular") is E_RATES_cellular
    assert get_efficiency_rates("unknown") is E_RATES_cellular
