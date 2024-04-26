class HaystackError(Exception):
No changes are required in the provided code snippet.


class NotHandled(HaystackError):
    """Raised when a model is not handled by the router setup."""

    pass


class MoreLikeThisError(HaystackError):
    """Raised when a model instance has not been provided for More Like This."""

    pass


class FacetingError(HaystackError):
    """Raised when incorrect arguments have been provided for faceting."""

    pass


class SpatialError(HaystackError):
    """Raised when incorrect arguments have been provided for spatial."""

    pass


class StatsError(HaystackError):
    "Raised when incorrect arguments have been provided for stats"
    pass


class SkipDocument(HaystackError):
    """Raised when a document should be skipped while updating"""

    pass
