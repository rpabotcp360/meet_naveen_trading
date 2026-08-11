from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings

IST = ZoneInfo(get_settings().market_timezone)
UTC = ZoneInfo("UTC")

SESSION_START = time(9, 15)
SIGNAL_ELIGIBILITY_START = time(9, 30)
STOP_NEW_SIGNALS = time(14, 45)
SESSION_END = time(15, 15)
OPENING_RANGE_END = time(9, 30)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST).astimezone(UTC)
    return dt.astimezone(UTC)


def to_ist(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC).astimezone(IST)
    return dt.astimezone(IST)


def ist_date(dt: datetime | None = None) -> date:
    return to_ist(dt or now_utc()).date()


def ist_time(dt: datetime | None = None) -> time:
    return to_ist(dt or now_utc()).time()


def is_within_time_range(t: time, start: time, end: time) -> bool:
    return start <= t < end


def is_opening_range(dt: datetime | None = None) -> bool:
    t = ist_time(dt)
    return is_within_time_range(t, SESSION_START, OPENING_RANGE_END)


def is_signal_eligible(dt: datetime | None = None) -> bool:
    t = ist_time(dt)
    return is_within_time_range(t, SIGNAL_ELIGIBILITY_START, STOP_NEW_SIGNALS)


def is_trading_session(dt: datetime | None = None) -> bool:
    t = ist_time(dt)
    return is_within_time_range(t, SESSION_START, SESSION_END)


def floor_to_interval(dt: datetime, minutes: int) -> datetime:
    dt_ist = to_ist(dt)
    total_minutes = dt_ist.hour * 60 + dt_ist.minute
    floored = (total_minutes // minutes) * minutes
    return dt_ist.replace(
        hour=floored // 60,
        minute=floored % 60,
        second=0,
        microsecond=0,
    )


def candle_close_utc(dt: datetime, minutes: int) -> datetime:
    start = floor_to_interval(dt, minutes)
    return to_utc(start + timedelta(minutes=minutes))
