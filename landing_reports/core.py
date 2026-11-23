"""GA4 landing reports. All data sources are explicit and read-only."""
from __future__ import annotations
import datetime as dt
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def validate_config(c):
    if not isinstance(c, dict): raise ValueError('config must be an object')
    prop = c.get('property_id')
    if not isinstance(prop, str) or not re.fullmatch(r'[0-9]+', prop): raise ValueError('property_id must be a numeric string')
    try: ZoneInfo(c['timezone'])
    except (KeyError, TypeError, ZoneInfoNotFoundError) as exc: raise ValueError('timezone must be a valid IANA timezone') from exc
    days = c.get('days')
    if type(days) is not int or not 1 <= days <= 365: raise ValueError('days must be an integer between 1 and 365')
    paths = c.get('paths')
    if not isinstance(paths, list) or not paths: raise ValueError('paths must be a nonempty list')
    seen = set()
    for item in paths:
        if not isinstance(item, dict): raise ValueError('each path must be an object')
        path = item.get('path'); label = item.get('label')
        if not isinstance(path, str) or not path.startswith('/') or path.startswith('//') or '?' in path or '#' in path or any(ord(ch)<32 for ch in path): raise ValueError('path must be an absolute path without query or fragment')
        if path in seen: raise ValueError('duplicate landing path')
        if not isinstance(label, str) or not label.strip() or '\n' in label: raise ValueError('label must be a nonempty single line')
        seen.add(path)
    for key in ('report_id','event_name','event_label','slack_channel_id','state_dir'):
        if not isinstance(c.get(key),str) or not c[key].strip() or '\n' in c[key]: raise ValueError(f'{key} is required')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', c['report_id']): raise ValueError('report_id must contain only letters, digits, hyphen or underscore')
    if not re.fullmatch(r'[A-Za-z0-9_]+', c['event_name']): raise ValueError('event_name must use letters, digits or underscore')
    return c


def periods(now, zone, days):
    if now.tzinfo is None: raise ValueError('now must be timezone aware')
    end = now.astimezone(ZoneInfo(zone)).date()-dt.timedelta(days=1)
    start = end-dt.timedelta(days=days-1)
    prev_end = start-dt.timedelta(days=1)
    prev_start = prev_end-dt.timedelta(days=days-1)
    return [(start.isoformat(),end.isoformat()),(prev_start.isoformat(),prev_end.isoformat())]


def validate_page(response, expected_timezone):
    if not isinstance(response,dict): raise ValueError('invalid GA4 response')
    if 'rowCount' not in response and not response.get('rows'): response = dict(response, rowCount=0)
    if type(response.get('rowCount')) is not int or response['rowCount'] < 0: raise ValueError('missing or invalid rowCount')
    metadata=response.get('metadata') or {}
    if metadata.get('timeZone') != expected_timezone: raise ValueError('GA4 timezone is absent or differs from configured timezone')
    if metadata.get('dataLossFromOtherRow') or metadata.get('subjectToThresholding') or metadata.get('samplingMetadatas') or metadata.get('dataTruncationReasons') or metadata.get('emptyReason') or metadata.get('schemaRestrictionResponse',{}).get('activeMetricRestrictions'):
        raise ValueError('GA4 data is sampled, thresholded, restricted or incomplete')
    if response.get('kind') and response['kind'] != 'analyticsData#runReport': raise ValueError('unexpected response kind')


def fetch_rows(post, property_id, timezone, start, end, metric, event=None, page_size=10000):
    if metric not in ('sessions','eventCount'): raise ValueError('unsupported metric')
    if metric == 'eventCount' and not event: raise ValueError('event required')
    body={'dateRanges':[{'startDate':start,'endDate':end}], 'dimensions':[{'name':'landingPage'}], 'metrics':[{'name':metric}], 'orderBys':[{'dimension':{'dimensionName':'landingPage'}}], 'limit':str(page_size), 'offset':'0', 'returnPropertyQuota':False}
    if event: body['dimensionFilter']={'filter':{'fieldName':'eventName','stringFilter':{'matchType':'EXACT','value':event,'caseSensitive':True}}}
    offset=0; total=None; rows={}
    while True:
        body['offset']=str(offset)
        response=post(property_id,body)
        validate_page(response,timezone)
        count=response.get('rowCount', 0 if not response.get('rows') else None)
        if total is None: total=count
        elif total != count: raise ValueError('GA4 row count changed while paginating')
        raw=response.get('rows',[])
        if not isinstance(raw,list) or len(raw)>page_size or offset+len(raw)>total: raise ValueError('invalid page size')
        if total and not raw: raise ValueError('GA4 pagination stopped before all rows')
        if (len(response.get('dimensionHeaders',[])) != 1 or response['dimensionHeaders'][0].get('name') != 'landingPage' or len(response.get('metricHeaders',[])) != 1 or response['metricHeaders'][0].get('name') != metric): raise ValueError('unexpected GA4 schema')
        for row in raw:
            dims=row.get('dimensionValues',[]); vals=row.get('metricValues',[])
            if len(dims)!=1 or len(vals)!=1 or not re.fullmatch(r'\d+',str(vals[0].get('value',''))): raise ValueError('invalid GA4 row')
            key=dims[0].get('value')
            if not isinstance(key,str) or key in rows: raise ValueError('duplicate or invalid GA4 row')
            rows[key]=int(vals[0]['value'])
        offset+=len(raw)
        if offset==total: return rows


def build_report(config, now, post):
    validate_config(config)
    windows=periods(now,config['timezone'],config['days'])
    values=[]
    for start,end in windows:
        sessions=fetch_rows(post,config['property_id'],config['timezone'],start,end,'sessions')
        events=fetch_rows(post,config['property_id'],config['timezone'],start,end,'eventCount',config['event_name'])
        values.append((sessions,events))
    entries=[]
    for p in config['paths']:
        path=p['path']; entries.append({'path':path,'label':p['label'],'sessions':values[0][0].get(path,0),'previous_sessions':values[1][0].get(path,0),'events':values[0][1].get(path,0),'previous_events':values[1][1].get(path,0)})
    return {'periods':windows,'timezone':config['timezone'],'event_name':config['event_name'],'event_label':config['event_label'],'rows':entries}


def render(report):
    (start,end),(old_start,old_end)=report['periods']
    lines=[f"GA4 landing report: {start}–{end} ({report['timezone']})",f"Previous: {old_start}–{old_end}",f"Event: {report['event_label']} ({report['event_name']})",'Sessions = GA4 sessions by landing page. Events = GA4 eventCount filtered by event name and grouped by landingPage; they are not unique converting sessions, confirmed purchases, or necessarily events on the landing page.','']
    for r in report['rows']:
        lines.append(f"{r['label']} ({r['path']}): sessions {r['sessions']} vs {r['previous_sessions']}; events {r['events']} vs {r['previous_events']}")
    return '\n'.join(lines)
