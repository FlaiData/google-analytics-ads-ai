"""Threshold alerts for comparable, completed report periods."""
import math


def evaluate(rows, rules, *, current_period, previous_period):
    """Return alerts. Rows have path and current/previous dicts containing metrics.

    Each rule has metric, direction ('increase' or 'decrease'), percent (0–10000),
    and min_previous (nonnegative). A zero baseline never produces an alert.
    Period labels must describe the periods supplied by the caller.
    """
    if not current_period or not previous_period:
        raise ValueError('both period labels are required')
    checked = []
    for rule in rules:
        metric = rule.get('metric')
        direction = rule.get('direction')
        threshold = rule.get('percent')
        baseline = rule.get('min_previous', 0)
        if metric not in ('sessions', 'events') or direction not in ('increase', 'decrease'):
            raise ValueError('unsupported alert metric or direction')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (threshold, baseline)):
            raise ValueError('thresholds must be finite numbers')
        if not 0 <= threshold <= 10000 or baseline < 0 or (direction == 'decrease' and threshold > 100):
            raise ValueError('threshold out of range')
        checked.append((metric, direction, threshold, baseline))
    result = []
    for row in rows:
        for metric, direction, threshold, baseline in checked:
            curr, prev = row['current'][metric], row['previous'][metric]
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 for x in (curr, prev)):
                raise ValueError('metric values must be nonnegative finite numbers')
            if not prev or prev < baseline:
                continue
            delta = (curr - prev) / prev * 100
            if not math.isfinite(delta):
                raise ValueError('percentage change is not finite')
            if (direction == 'increase' and delta >= threshold and curr > prev) or (direction == 'decrease' and delta <= -threshold and curr < prev):
                result.append({'path': row['path'], 'metric': metric, 'direction': direction,
                               'current': curr, 'previous': prev, 'change_percent': delta,
                               'current_period': current_period, 'previous_period': previous_period})
    return result


def safe_failure_message(error):
    """Return a constant diagnostic category; never include exception content."""
    if isinstance(error, TimeoutError): category = 'timeout'
    elif isinstance(error, ConnectionError): category = 'connection'
    elif isinstance(error, ValueError): category = 'validation'
    else: category = 'other'
    return f'Report delivery failed ({category}). Check the server logs.'
