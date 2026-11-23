"""At-most-once Slack delivery. Ambiguous outcomes require manual reconciliation."""
import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ReconciliationRequired(RuntimeError):
    pass


def slack_post(token, channel, text, thread_ts=None):
    payload = {'channel': channel, 'text': text, 'unfurl_links': 'false', 'unfurl_media': 'false'}
    if thread_ts:
        payload['thread_ts'] = thread_ts
    request = Request('https://slack.com/api/chat.postMessage', data=urlencode(payload).encode(),
                      headers={'Authorization': 'Bearer ' + token})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not result.get('ok') or result.get('channel') != channel or not result.get('ts'):
        raise RuntimeError('Slack did not confirm the requested destination')
    return result['ts']


def _write(path, state):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.delivery-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def deliver(parts, *, channel, report_key, token, state_dir, post=slack_post):
    """Send one report at most once per key and channel; returns Slack timestamps.

    A crash or exception while a request is in flight leaves an uncertain state.
    Inspect Slack and reconcile the state manually before another attempt.
    """
    if not channel or not report_key or not token or not parts or any(not isinstance(p, str) or not p.strip() for p in parts):
        raise ValueError('channel, report key, token and nonempty text parts are required')
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    identity = hashlib.sha256((channel + '\0' + report_key).encode()).hexdigest()
    path = state_dir / (identity + '.json')
    digest = hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()
    with (state_dir / (identity + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            state = json.loads(path.read_text())
            if state.get('channel') != channel or state.get('report_key') != report_key:
                raise ReconciliationRequired('State identity mismatch')
            if state.get('status') == 'sent':
                return state['timestamps']
            if state.get('status') != 'pending' or state.get('digest') != digest:
                raise ReconciliationRequired('Inspect Slack and reconcile the delivery state')
        else:
            state = {'channel': channel, 'report_key': report_key, 'digest': digest, 'status': 'pending', 'timestamps': []}
            _write(path, state)
        for part in parts[len(state['timestamps']):]:
            state['status'] = 'needs_reconciliation'
            _write(path, state)
            ts = post(token, channel, part, state['timestamps'][0] if state['timestamps'] else None)
            if not isinstance(ts, str) or not ts:
                raise ReconciliationRequired('Slack returned no timestamp')
            state['timestamps'].append(ts)
            state['status'] = 'sent' if len(state['timestamps']) == len(parts) else 'pending'
            _write(path, state)
        return state['timestamps']
