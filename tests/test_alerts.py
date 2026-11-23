import math
import unittest
from landing_reports.alerts import evaluate, safe_failure_message

class AlertTests(unittest.TestCase):
    def setUp(self):
        self.row={'path':'/example', 'current':{'sessions':50,'events':12}, 'previous':{'sessions':100,'events':10}}
        self.periods=dict(current_period='2026-01-08 to 2026-01-14', previous_period='2026-01-01 to 2026-01-07')
    def test_separate_rules_and_periods(self):
        rules=[{'metric':'sessions','direction':'decrease','percent':40,'min_previous':50}, {'metric':'events','direction':'increase','percent':20,'min_previous':10}]
        a=evaluate([self.row],rules,**self.periods)
        self.assertEqual([x['change_percent'] for x in a],[-50,20])
        self.assertEqual(a[0]['previous_period'],self.periods['previous_period'])
    def test_no_zero_or_small_baseline(self):
        self.row['previous']['events']=0
        rules=[{'metric':'events','direction':'increase','percent':1}, {'metric':'sessions','direction':'decrease','percent':1,'min_previous':101}]
        self.assertEqual(evaluate([self.row],rules,**self.periods),[])
    def test_invalid_bounds(self):
        for v in (math.nan, math.inf, -1, 101):
            with self.subTest(v=v), self.assertRaises(ValueError):
                evaluate([self.row],[{'metric':'sessions','direction':'decrease','percent':v}],**self.periods)
    def test_secret_not_in_failure(self):
        self.assertEqual(safe_failure_message(TimeoutError('secret-value')), 'Report delivery failed (timeout). Check the server logs.')
        self.assertNotIn('secret-value', safe_failure_message(Exception('secret-value')))
