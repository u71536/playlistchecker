import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIMEZONES = (
    ('UTC', 'UTC'),
    ('Europe/Kaliningrad', 'Kaliningrad'),
    ('Europe/Moscow', 'Moscow'),
    ('Europe/Samara', 'Samara'),
    ('Asia/Yekaterinburg', 'Yekaterinburg'),
    ('Asia/Omsk', 'Omsk'),
    ('Asia/Krasnoyarsk', 'Krasnoyarsk'),
    ('Asia/Irkutsk', 'Irkutsk'),
    ('Asia/Yakutsk', 'Yakutsk'),
    ('Asia/Vladivostok', 'Vladivostok'),
    ('Asia/Magadan', 'Magadan'),
    ('Asia/Kamchatka', 'Kamchatka'),
    ('Europe/London', 'London'),
    ('Europe/Berlin', 'Berlin'),
    ('America/New_York', 'New York'),
    ('America/Los_Angeles', 'Los Angeles'),
)


def default_check_hour():
    raw = os.environ.get('CHECK_HOUR', '9')
    try:
        hour = int(raw)
    except (TypeError, ValueError):
        return 9
    if 0 <= hour <= 23:
        return hour
    return 9


def zone_for(timezone_name):
    try:
        return ZoneInfo(timezone_name or 'UTC')
    except ZoneInfoNotFoundError:
        return ZoneInfo('UTC')


def is_due(check_hour, timezone_name, moment=None):
    """True when the user's local hour matches the hour they chose."""
    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local = current.astimezone(zone_for(timezone_name))
    hour = default_check_hour() if check_hour is None else check_hour
    return local.hour == hour
