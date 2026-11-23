import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from manual_changes.__main__ import CONFIG, check_config, make_spec, perform, read_plan

CHECKSUM = 'a' * 64
PLAN = {'customer_id': '1234567890', 'name': 'Example', 'description': 'Test', 'background_color': '#AABBCC'}


def proposal(plan=PLAN):
    items = [{'operation': 'CREATE', 'entity_readable': 'Label', 'primary_key_readable': plan['name'], 'field_readable': field, 'value_readable': value} for field, value in [('Name', plan['name']), ('Description', plan['description']), ('Background Color', plan['background_color'])]]
    return {'status': 'PROPOSED', 'validate_only': True, 'customer_id': plan['customer_id'], 'checksum': CHECKSUM, 'change_items': items}


def response(value, error=False):
    return SimpleNamespace(isError=error, content=[SimpleNamespace(type='text', text=value)])


class Session:
    def __init__(self, value=None, fail_commit=False):
        self.calls = []
        self.value = proposal() if value is None else value
        self.fail_commit = fail_commit

    async def call_tool(self, tool, arguments):
        self.calls.append((tool, arguments))
        if arguments['validate_only']:
            return response(json.dumps(self.value))
        if self.fail_commit:
            raise TimeoutError()
        return response('Created')


class ManualChangesTests(unittest.TestCase):
    def run_flow(self, session, answer, compute=lambda customer, payload: CHECKSUM, check=lambda: None):
        out = []
        asyncio.run(perform(session, PLAN, '9876543210', compute, lambda prompt: answer, out.append, check))
        return out

    def test_approved_binds_arguments_and_checksum(self):
        session = Session()
        received = []
        def compute(customer, payload):
            received.append((customer, payload))
            return CHECKSUM
        self.run_flow(session, 'APPROVE 1234567890 ' + CHECKSUM, compute)
        self.assertEqual(len(session.calls), 2)
        first, second = [args for _, args in session.calls]
        self.assertEqual({k: v for k, v in second.items() if k not in ('validate_only', 'checksum')}, {k: v for k, v in first.items() if k != 'validate_only'})
        self.assertIs(first['validate_only'], True)
        self.assertIs(second['validate_only'], False)
        self.assertEqual(second['checksum'], CHECKSUM)
        self.assertEqual(received[0][1], {'tool': 'manage_labels', 'operation': 'CREATE', 'name': 'Example', 'description': 'Test', 'background_color': '#AABBCC', 'label_id': None})
        self.assertEqual(first['login_customer_id'], '9876543210')

    def test_bad_approvals_do_not_write(self):
        for answer in ('', 'approve 1234567890 ' + CHECKSUM, 'APPROVE 1234567891 ' + CHECKSUM, 'APPROVE 1234567890 ' + CHECKSUM[:-1], 'APPROVE 1234567890 ' + CHECKSUM + ' '):
            with self.subTest(answer=answer):
                session = Session()
                with self.assertRaises(ValueError): self.run_flow(session, answer)
                self.assertEqual(len(session.calls), 1)

    def test_rejects_mismatched_checksum_and_proposal(self):
        for mutation in (lambda p: p.update(checksum='b' * 64), lambda p: p.update(customer_id='1111111111'), lambda p: p['change_items'][0].update(value_readable='wrong')):
            p = proposal()
            mutation(p)
            session = Session(p)
            with self.assertRaises(ValueError): self.run_flow(session, 'APPROVE 1234567890 ' + CHECKSUM)
            self.assertEqual(len(session.calls), 1)

    def test_commit_failure_no_retry(self):
        session = Session(fail_commit=True)
        with self.assertRaisesRegex(RuntimeError, 'outcome unknown'):
            self.run_flow(session, 'APPROVE 1234567890 ' + CHECKSUM)
        self.assertEqual(len(session.calls), 2)

    def test_config_integrity_before_commit(self):
        calls = []
        def check():
            calls.append(1)
            if len(calls) == 2: raise ValueError('changed')
        session = Session()
        with self.assertRaises(ValueError): self.run_flow(session, 'APPROVE 1234567890 ' + CHECKSUM, check=check)
        self.assertEqual(len(session.calls), 1)

    def test_private_plan_and_config(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            path.write_text(json.dumps(PLAN))
            path.chmod(0o600)
            self.assertEqual(read_plan(str(path)), PLAN)
            path.write_text(json.dumps({**PLAN, 'operation': 'REMOVE'}))
            with self.assertRaises(ValueError): read_plan(str(path))
            cfg = Path(temp) / 'config.yaml'
            cfg.write_bytes(CONFIG)
            cfg.chmod(0o400)
            check_config(cfg)
            cfg.chmod(0o600)
            with self.assertRaises(ValueError): check_config(cfg)

    def test_only_user_credentials(self):
        with TemporaryDirectory() as temp:
            cred = Path(temp) / 'credentials.json'
            profile = Path(temp) / 'profile.json'
            cred.write_text('{"type":"service_account"}')
            profile.write_text(json.dumps({'ads': {'credentials_file': str(cred)}}))
            cred.chmod(0o600)
            profile.chmod(0o600)
            with patch('manual_changes.__main__.launch_spec') as launch:
                with self.assertRaises(ValueError): make_spec(str(profile))
                launch.assert_not_called()

    def test_no_tty(self):
        from manual_changes.__main__ import main
        with patch('sys.argv', ['manual_changes', '--profile', '/x', '--plan', '/y']), patch('sys.stdin.isatty', return_value=False), patch('manual_changes.__main__.run') as run:
            self.assertEqual(main(), 1)
            run.assert_not_called()
