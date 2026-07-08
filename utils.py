from datetime import date, timedelta


def week_start_for(d: date) -> date:
    """Returns the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def week_range(week_start: date):
    """Returns (start, end) inclusive, Monday-Sunday."""
    return week_start, week_start + timedelta(days=6)


def format_naira(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0
    return "\u20a6{:,.2f}".format(value)


def parse_date(value, default):
    from datetime import datetime
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default
