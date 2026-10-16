"""Observation-age rules for persisted economic and market snapshots."""
from datetime import date, datetime, timedelta, timezone


ANNUAL_MAX_AGE = timedelta(days=550)
MONTHLY_MAX_AGE = timedelta(days=62)
TICKER_OBSERVATION_MAX_AGE = timedelta(days=3)


def observation_date(value: str | date | datetime) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def is_observation_stale(
    value: str | date | datetime | None,
    *,
    frequency: str = "annual",
    now: datetime | None = None,
) -> bool:
    """Treat invalid dates as stale and compare with a frequency-aware age limit."""
    observed = observation_date(value) if value is not None else None
    if observed is None:
        return True

    current = now or datetime.now(timezone.utc)
    current_date = current.date()
    max_age = MONTHLY_MAX_AGE if frequency == "monthly" else ANNUAL_MAX_AGE
    return current_date - observed > max_age


def is_ticker_observation_stale(
    value: str | date | datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """A missing or older-than-three-calendar-day Yahoo bar is never called fresh."""
    observed = observation_date(value) if value is not None else None
    if observed is None:
        return True
    current = now or datetime.now(timezone.utc)
    age = current.date() - observed
    return age.days < 0 or age > TICKER_OBSERVATION_MAX_AGE
