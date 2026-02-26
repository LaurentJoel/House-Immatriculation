"""
Input validation and sanitization utilities.

Protects against:
- XSS (HTML/script injection via bleach)
- SQL injection (parameterised queries are used, but we sanitize as defence-in-depth)
- Oversized inputs
- Invalid data types / ranges
"""
import re
from typing import Any, Optional

import bleach

# ── Sanitization ─────────────────────────────────────────────────

def sanitize_string(value: Any, max_length: int = 200) -> str:
    """Strip HTML tags, trim whitespace, enforce max length.

    Script/style content is removed entirely, not just tags.
    """
    if not isinstance(value, str):
        return ''
    # First remove <script>...</script> and <style>...</style> content entirely
    import re
    cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', value, flags=re.IGNORECASE | re.DOTALL)
    # Then strip any remaining HTML tags
    cleaned = bleach.clean(cleaned, tags=[], attributes={}, strip=True)
    return cleaned.strip()[:max_length]


def sanitize_phone(value: Any) -> str:
    """Allow only digits, +, -, spaces, and parens in phone numbers."""
    if not isinstance(value, str):
        return ''
    cleaned = re.sub(r'[^\d+\-() ]', '', value)
    return cleaned[:20]


# ── Validation ───────────────────────────────────────────────────

def validate_latitude(val: Any) -> Optional[float]:
    """Return a valid latitude or None."""
    try:
        lat = float(val)
    except (TypeError, ValueError):
        return None
    if -90.0 <= lat <= 90.0:
        return lat
    return None


def validate_longitude(val: Any) -> Optional[float]:
    """Return a valid longitude or None."""
    try:
        lon = float(val)
    except (TypeError, ValueError):
        return None
    if -180.0 <= lon <= 180.0:
        return lon
    return None


def validate_positive_int(val: Any, max_val: int = 999999) -> Optional[int]:
    """Return a positive integer within bounds, or None."""
    try:
        n = int(val)
    except (TypeError, ValueError):
        return None
    if 0 < n <= max_val:
        return n
    return None


def validate_positive_float(val: Any, max_val: float = 1e9) -> Optional[float]:
    """Return a positive float within bounds, or None."""
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if 0 < f <= max_val:
        return f
    return None


def validate_enum(val: Any, allowed: tuple | list) -> Optional[str]:
    """Return the value if it is in the allowed set, else None."""
    if val in allowed:
        return val
    return None
