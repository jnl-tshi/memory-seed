"""strutil - small stdlib-only string and settings utilities."""

from strutil.text import slugify, truncate
from strutil.config import load_settings

__all__ = ["slugify", "truncate", "load_settings"]
