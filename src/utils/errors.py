"""Custom exception types for consistent error handling."""


class FirestoreUnavailableError(Exception):
    """Raised when Firestore queries fail or are unavailable."""


class InvalidInputError(Exception):
    """Raised when request input validation fails."""


class LLMError(Exception):
    """Raised when an LLM call fails or returns invalid output."""


class GraphExecutionError(Exception):
    """Raised when a graph fails to compile or execute."""
