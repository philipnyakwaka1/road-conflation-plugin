"""
Algorithm constants and configuration values.

This module defines the efficiency rate coefficients used in the conflation algorithm. These 
parameters control the relative contribution of individual similarity metrics during feature
matching.
"""

E_RATES_tree = {
    'H': 2.00000,  # Hausdorff
    'O': 1.28409,  # Orientation
    'S': 1.03978 , # Sinuosity
    'P': 1.00000,  # Mean Perpendicular Distance
    'T': 1.03356,  # Mean length of triangle edges
    'C': 1.08765   # Modified degree of connectivity
}

E_RATES_cellular = {
    'H': 2.00000,
    'O': 1.16961,
    'S': 1.00000,
    'P': 1.00000,
    'T': 1.11875,
    'C': 1.17006
}

E_RATES_hybrid = {
    'H': 1.64067,
    'O': 1.32845,
    'S': 1.01742,
    'P': 1.00000,
    'T': 1.00000,
    'C': 1.02644
}

def get_efficiency_rates(pattern: str) -> dict:
	"""Returns the efficiency rates based on the specified pattern."""
	if pattern == 'tree':
		return E_RATES_tree
	elif pattern == 'hybrid':
		return E_RATES_hybrid
	else:
		return E_RATES_cellular