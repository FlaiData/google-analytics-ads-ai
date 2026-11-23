import contextlib,datetime as dt,io,unittest
from copy import deepcopy
from unittest.mock import patch
from landing_reports.__main__ import execute
from tests.test_core import CFG,page

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.cfg=deepcopy(CFG);self.cfg.update({'alert_channel_id':'C0123456789','alert_rules':[{'metric':'sessions','direction':'decrease','percent':20,'min_previous':10}]})
        self.calls=[]
    def post(self,prop,body):
        metric=body['metrics'][0]['name']; start=body['dateRanges'][0]['startDate']; val=80 if start=='2026-06-01' else 100
        return page(metric,[('/example-ad',val)])
    def send(self,payload,**kwargs):self.calls.append((payload,kwargs))
    def test_report_and_threshold_alert_are_separate(self):
        execute(self.cfg,dt.datetime(2026,6,4,12,tzinfo=dt.timezone.utc),self.post,token='mock',sender=self.send)
        self.assertEqual(len(self.calls),2)
        self.assertIn('threshold:',self.calls[1][1]['report_key'])
        self.assertIn('-20.0%',self.calls[1][0][0])
    def test_preview_never_sends(self):
        with contextlib.redirect_stdout(io.StringIO()): execute(self.cfg,dt.datetime(2026,6,4,12,tzinfo=dt.timezone.utc),self.post,preview=True,sender=self.send)
        self.assertEqual(self.calls,[])
    def test_invalid_report_never_sends(self):
        def bad(p,b):return page('sessions',[('/example-ad',1)],metadata={'subjectToThresholding':True})
        with self.assertRaises(ValueError):execute(self.cfg,dt.datetime(2026,6,4,12,tzinfo=dt.timezone.utc),bad,token='mock',sender=self.send)
        self.assertEqual(self.calls,[])

class FailureNotificationTests(unittest.TestCase):
    def test_failed_ga4_emits_safe_notification_and_nonzero_exit(self):
        import json,os,tempfile,types
        import landing_reports.__main__ as cli
        cfg=deepcopy(CFG);cfg.update({'alert_channel_id':'C0123456789','alert_rules':[]})
        with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
            json.dump(cfg,f);f.flush()
            def broken(prop, body): raise ValueError('sensitive details must not leak')
            fake=types.ModuleType('landing_reports.ga4');fake.client=lambda:broken
            with patch.dict('sys.modules',{'landing_reports.ga4':fake}), patch.dict(os.environ,{'SLACK_BOT_TOKEN':'mock'}),patch.object(cli,'deliver') as sender,contextlib.redirect_stderr(io.StringIO()):
                result=cli.main(['--config',f.name])
            self.assertEqual(result,1);sender.assert_called_once()
            self.assertNotIn('sensitive details',str(sender.call_args))
            self.assertEqual(sender.call_args.kwargs['channel'],cfg['alert_channel_id'])

class StableIdentityTests(unittest.TestCase):
    def test_page_and_label_edits_do_not_create_new_delivery_key(self):
        from landing_reports.__main__ import identity
        a=deepcopy(CFG);b=deepcopy(a);b['paths'][0]['label']='Changed';b['paths'].append({'path':'/other','label':'Other'});b['event_name']='new_event'
        self.assertEqual(identity(a,'2026-06-03'),identity(b,'2026-06-03'))
        b['report_id']='other-report'
        self.assertNotEqual(identity(a,'2026-06-03'),identity(b,'2026-06-03'))
