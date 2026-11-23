import datetime as dt
import unittest
from copy import deepcopy
from landing_reports.core import validate_config, periods, fetch_rows, build_report, render

CFG={'report_id':'example-landings','property_id':'123456789','timezone':'America/New_York','days':3,'paths':[{'path':'/example-ad','label':'Example'}], 'event_name':'ticket_click','event_label':'Ticket clicks','slack_channel_id':'C0123456789','state_dir':'/data'}

def page(metric, values, count=None, metadata=None):
    result={'rowCount':len(values) if count is None else count,'metadata':{'timeZone':'America/New_York'},'dimensionHeaders':[{'name':'landingPage'}],'metricHeaders':[{'name':metric}],'rows':[{'dimensionValues':[{'value':k}],'metricValues':[{'value':str(v)}]} for k,v in values]}
    if metadata: result['metadata'].update(metadata)
    return result

class CoreTests(unittest.TestCase):
    def test_periods_are_disjoint_and_use_property_timezone(self):
        now=dt.datetime(2026,3,9,3,tzinfo=dt.timezone.utc)
        self.assertEqual(periods(now,'America/New_York',3), [('2026-03-05','2026-03-07'),('2026-03-02','2026-03-04')])
    def test_config_rejects_duplicate_and_query_path(self):
        c=deepcopy(CFG);c['paths'].append(dict(c['paths'][0]))
        with self.assertRaises(ValueError):validate_config(c)
        c=deepcopy(CFG);c['paths'][0]['path']='/ad?x=1'
        with self.assertRaises(ValueError):validate_config(c)
    def test_paginate_with_stable_order_and_filter(self):
        calls=[]
        def post(prop,body):
            calls.append(deepcopy(body))
            return page('eventCount',[('/a',2)] if body['offset']=='0' else [('/b',3)],2)
        self.assertEqual(fetch_rows(post,'123','America/New_York','2026-01-01','2026-01-03','eventCount','click',page_size=1),{'/a':2,'/b':3})
        self.assertEqual(calls[1]['offset'],'1')
        self.assertEqual(calls[0]['orderBys'][0]['dimension']['dimensionName'],'landingPage')
        self.assertEqual(calls[0]['dimensionFilter']['filter']['fieldName'],'eventName')
    def test_second_page_thresholding_is_rejected(self):
        def post(p,b):return page('sessions',[('/a',1)] if b['offset']=='0' else [('/b',1)],2,{} if b['offset']=='0' else {'subjectToThresholding':True})
        with self.assertRaises(ValueError):fetch_rows(post,'123','America/New_York','a','b','sessions',page_size=1)
    def test_incomplete_and_duplicates_are_rejected(self):
        with self.assertRaises(ValueError):fetch_rows(lambda p,b:page('sessions',[('/a',1)] if b['offset']=='0' else [],2),'123','America/New_York','a','b','sessions',page_size=1)
        with self.assertRaises(ValueError):fetch_rows(lambda p,b:page('sessions',[('/a',1)],2),'123','America/New_York','a','b','sessions',page_size=1)
    def test_wrong_timezone_and_sampling_rejected(self):
        for meta in ({'timeZone':'UTC'},{'samplingMetadatas':[{}]},{'dataLossFromOtherRow':True},{'emptyReason':'unavailable'}):
            with self.subTest(meta=meta),self.assertRaises(ValueError):fetch_rows(lambda p,b:page('sessions',[('/a',1)],metadata=meta),'123','America/New_York','a','b','sessions')
    def test_zero_count_omitted_proto_is_valid(self):
        def post(p,b):
            result=page('sessions',[]);del result['rowCount'];return result
        self.assertEqual(fetch_rows(post,'123','America/New_York','a','b','sessions'),{})
    def test_event_count_never_described_as_converting_sessions(self):
        def post(p,b):
            metric=b['metrics'][0]['name'];val=5 if metric=='sessions' else 8
            return page(metric,[('/example-ad',val)])
        r=build_report(CFG,dt.datetime(2026,6,9,tzinfo=dt.timezone.utc),post)
        self.assertEqual(r['rows'][0]['sessions'],5);self.assertEqual(r['rows'][0]['events'],8)
        self.assertIn('not unique converting sessions',render(r))
        self.assertNotIn('CR ',render(r))

if __name__=='__main__':unittest.main()
