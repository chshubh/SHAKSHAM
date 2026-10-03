from datetime import date, timedelta


def calculate_completion(completed, total):
    if total <= 0:
        return 0
    return round((completed / total) * 100)


def streak(days, today=None):
    """Consecutive active days ending today (or yesterday, so a streak isn't lost mid-day)."""
    today = today or date.today()
    days = set(days)
    cur = today if today in days else today - timedelta(days=1)
    n = 0
    while cur in days:
        n += 1
        cur -= timedelta(days=1)
    return n


def minutes_by_day(rows, today=None, n=7):
    """rows: iterable of (date, seconds). Returns [(date, minutes)] for the last n days."""
    today = today or date.today()
    totals = {}
    for d, secs in rows:
        totals[d] = totals.get(d, 0) + secs
    return [(today - timedelta(days=i), round(totals.get(today - timedelta(days=i), 0) / 60))
            for i in range(n - 1, -1, -1)]


def minutes_by_week(rows, today=None, n=8):
    today = today or date.today()
    start = today - timedelta(days=today.weekday())      # Monday of this week
    weeks = []
    for i in range(n - 1, -1, -1):
        ws = start - timedelta(weeks=i)
        secs = sum(s for d, s in rows if ws <= d < ws + timedelta(days=7))
        weeks.append((ws, round(secs / 60)))
    return weeks
