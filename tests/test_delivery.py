import json
import tempfile
import unittest
from pathlib import Path
from landing_reports.delivery import deliver, ReconciliationRequired

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.args = dict(channel='CEXAMPLE', report_key='2026-01-01', token='example', state_dir=self.tmp.name)

    def test_parts_and_duplicate(self):
        calls = []
        def post(token, channel, text, thread):
            calls.append((text, thread)); return str(len(calls))
        self.assertEqual(deliver(['first','second'], post=post, **self.args), ['1','2'])
        self.assertEqual(calls, [('first', None), ('second', '1')])
        self.assertEqual(deliver(['first','second'], post=post, **self.args), ['1','2'])
        self.assertEqual(len(calls), 2)

    def test_ambiguous_send_fails_closed(self):
        def fail(*args): raise TimeoutError('unknown outcome')
        with self.assertRaises(TimeoutError): deliver(['first'], post=fail, **self.args)
        with self.assertRaises(ReconciliationRequired): deliver(['first'], post=lambda *a:'unexpected', **self.args)
        state=json.loads(next(Path(self.tmp.name).glob('*.json')).read_text())
        self.assertEqual(state['status'], 'needs_reconciliation')

    def test_distinct_destination_has_distinct_state(self):
        call=[]
        def post(*args):call.append(1);return str(len(call))
        deliver(['x'],post=post,**self.args)
        self.args['channel']='COTHER'
        deliver(['x'],post=post,**self.args)
        self.assertEqual(len(call),2)

if __name__ == '__main__': unittest.main()
