"""String helpers. Stdlib only."""

import re

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Lowercase, collapse non-alphanumerics to single hyphens, trim hyphens."""
    lowered = value.strip().lower()
    collapsed = _SLUG_STRIP.sub("-", lowered)
    return collapsed.strip("-")


def truncate(value: str, limit: int, ellipsis: str = "...") -> str:
    """Truncate to at most `limit` characters, appending `ellipsis` when cut.

    The ellipsis counts toward the limit. A limit shorter than the ellipsis
    returns a bare slice.
    """
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if len(value) <= limit:
        return value
    if limit <= len(ellipsis):
        return value[:limit]
    return value[: limit - len(ellipsis)] + ellipsis
