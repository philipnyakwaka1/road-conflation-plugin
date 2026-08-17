"""
This module defines custom exceptions used in the road conflation process.
"""

class NoMatchesFoundException(Exception):
	"""Custom exception raised when no candidate matches are found during the conflation process."""
	pass

class ConflationCancelledException(Exception):
    """Raised when the user cancels the conflation process."""
    pass