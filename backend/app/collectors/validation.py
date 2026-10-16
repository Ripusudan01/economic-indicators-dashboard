"""Validation helpers for values returned by fixed upstream indicator APIs."""
import math
import re


_YEAR_PATTERN = re.compile(r"^\d{4}$")


def valid_year(value: object) -> str:
    year = str(value)
    if not _YEAR_PATTERN.fullmatch(year) or not 1800 <= int(year) <= 2200:
        raise ValueError("Upstream response contained an invalid year")
    return year


def finite_number(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Upstream response contained a non-numeric value") from exc
    if not math.isfinite(number):
        raise ValueError("Upstream response contained a non-finite value")
    return number
