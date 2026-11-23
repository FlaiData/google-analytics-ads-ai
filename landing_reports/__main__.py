"""Command line entry point; run on a schedule with an external scheduler."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
import sys

from . import alerts
from .core import build_report, periods, render, validate_config
from .delivery import deliver


def load_config(path):
    with open(path, encoding='utf-8') as handle: config=json.load(handle)
    validate_config(config)
    rules=config.get('alert_rules',[])
    if not isinstance(rules,list): raise ValueError('alert_rules must be a list')
    if not isinstance(config.get('alert_channel_id'),str) or not config['alert_channel_id'].strip(): raise ValueError('alert_channel_id is required')
    alerts.evaluate([],rules,current_period='current',previous_period='previous')
    return config


def identity(config, end):
    # Stable report identity: label and query changes must not create duplicate sends.
    key=json.dumps([config['report_id'],config['property_id'],config['timezone'],config['days']],sort_keys=True,ensure_ascii=False)
    return hashlib.sha256(key.encode()).hexdigest() + ':' + end


def parts(text, limit=3500):
    lines=text.splitlines(); out=[]; chunk=''
    for line in lines:
        if len(line)>limit: raise ValueError('report line is too long')
        candidate=chunk+'\n'+line if chunk else line
        if len(candidate)>limit:
            out.append(chunk); chunk=line
        else: chunk=candidate
    if chunk: out.append(chunk)
    if not out: raise ValueError('empty message')
    return out


def execute(config, now, post, token=None, preview=False, sender=deliver):
    result=build_report(config,now,post)
    current,previous=result['periods']
    rows=[{'path':r['path'], 'current':{'sessions':r['sessions'],'events':r['events']}, 'previous':{'sessions':r['previous_sessions'],'events':r['previous_events']}} for r in result['rows']]
    hits=alerts.evaluate(rows,config.get('alert_rules',[]),current_period='–'.join(current),previous_period='–'.join(previous))
    message=render(result)
    if preview:
        print(message)
        if hits: print('\nThreshold alerts:',json.dumps(hits,ensure_ascii=False))
        return
    if not token: raise ValueError('SLACK_BOT_TOKEN is required')
    key=identity(config,current[1])
    sender(parts(message),channel=config['slack_channel_id'],report_key='report:'+key,token=token,state_dir=config['state_dir'])
    if hits:
        lines=['GA4 threshold alerts',f'Current: {current[0]}–{current[1]}; previous: {previous[0]}–{previous[1]}']
        for hit in hits:
            lines.append(f"{hit['path']}: {hit['metric']} {hit['previous']} → {hit['current']} ({hit['change_percent']:+.1f}%)")
        sender(parts('\n'.join(lines)),channel=config['alert_channel_id'],report_key='threshold:'+key,token=token,state_dir=config['state_dir'])
    print('Report processed; see delivery state for confirmation.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--preview',action='store_true',help='read GA4 and print; do not send')
    args=parser.parse_args(argv)
    config=None; now=dt.datetime.now(dt.timezone.utc); token=os.environ.get('SLACK_BOT_TOKEN'); stage='configuration'
    try:
        config=load_config(args.config)
        stage='GA4 setup'
        from .ga4 import client
        post=client()
        stage='GA4 query, report or Slack delivery'
        execute(config,now,post,token=token,preview=args.preview)
        return 0
    except Exception as exc:
        # Never disclose API responses or secrets in logs or alerts.
        print('Job failed at',stage,'(',type(exc).__name__,'). Check configuration, access and delivery state.',file=sys.stderr)
        if not args.preview and config and token:
            try:
                end=periods(now,config['timezone'],config['days'])[0][1]
                failure_key='failure:'+identity(config,end)+':'+type(exc).__name__
                deliver([alerts.safe_failure_message(exc)],channel=config['alert_channel_id'],report_key=failure_key,token=token,state_dir=config['state_dir'])
            except Exception as alert_exc:
                print('Failure notification unavailable:',type(alert_exc).__name__,file=sys.stderr)
        return 1

if __name__=='__main__': raise SystemExit(main())
