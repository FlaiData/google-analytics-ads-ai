import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from integrations import launch


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.creds = self.root/'creds.json'
        self.creds.write_text(json.dumps({'type':'authorized_user','client_id':'fake','client_secret':'fake','refresh_token':'fake'}))
        self.creds.chmod(0o600)
        self.token = self.root/'token.txt'; self.token.write_text('dummy_token_value'); self.token.chmod(0o600)
        self.profile = self.root/'profile.json'
        self.data={'analytics':{'credentials_file':str(self.creds),'cloud_project':'sample-project'},'ads':{'credentials_file':str(self.creds),'developer_token_file':str(self.token),'login_customer_id':'1234567890'}}
        self.save()
        self.version=lambda name: dict(analytics_mcp='1.1.0', google_ads_mcp='0.0.6')[name.replace('-','_')]
    def tearDown(self): self.temp.cleanup()
    def save(self): self.profile.write_text(json.dumps(self.data)); self.profile.chmod(0o600)
    def launch(self, server, environ=None): return launch.launch_spec(str(self.profile),server,environ=environ or {},get_version=self.version)
    def test_analytics_forces_read_only_and_clears_dangerous_env(self):
        cmd,env=self.launch('analytics',{'ANALYTICS_MCP_ALLOW_WRITE':'true','ANALYTICS_MCP_OAUTH':'true','GOOGLE_OAUTH_CLIENT_SECRET':'secret','GOOGLE_ADS_MCP_OAUTH_CLIENT_ID':'other','PYTHONPATH':'evil','PATH':'/usr/bin'})
        self.assertEqual(env['ANALYTICS_MCP_ALLOW_WRITE'],'false'); self.assertEqual(env['ANALYTICS_MCP_OAUTH'],'false')
        self.assertEqual(env['GOOGLE_APPLICATION_CREDENTIALS'],str(self.creds))
        self.assertNotIn('GOOGLE_OAUTH_CLIENT_SECRET',env);self.assertNotIn('PYTHONPATH',env);self.assertNotIn('GOOGLE_ADS_MCP_OAUTH_CLIENT_ID',env)
        self.assertIn('-I',cmd)
    def test_ads_removes_oauth_proxy_and_uses_locked_config(self):
        cmd,env=self.launch('ads',{'GOOGLE_ADS_MCP_TOOLS_CONFIG':'/unsafe','GOOGLE_ADS_MCP_OAUTH_CLIENT_ID':'evil','GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET':'secret','GOOGLE_ADS_DEVELOPER_TOKEN':'wrong','GOOGLE_ADS_LOGIN_CUSTOMER_ID':'9999999999'})
        self.assertEqual(env['GOOGLE_ADS_MCP_TOOLS_CONFIG'],str(launch.READ_ONLY_PATH))
        self.assertEqual(env['GOOGLE_ADS_DEVELOPER_TOKEN'],'dummy_token_value')
        self.assertEqual(env['GOOGLE_ADS_LOGIN_CUSTOMER_ID'],'1234567890')
        self.assertNotIn('GOOGLE_ADS_MCP_OAUTH_CLIENT_ID',env);self.assertNotIn('GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET',env)
        self.assertEqual(launch.READ_ONLY_PATH.read_bytes(),launch.READ_ONLY_CONFIG)
    def test_explicit_ca_is_isolated_and_applied_to_both_servers(self):
        bundle = self.root/'ca.pem'; bundle.write_text('synthetic')
        for section in self.data.values(): section['ca_bundle_file'] = str(bundle)
        self.save()
        with patch.object(launch.ssl, 'create_default_context') as validate:
            for server in ('analytics', 'ads'):
                _, env = self.launch(server, {'SSL_CERT_FILE':'/old', 'SSL_CERT_DIR':'/old-dir', 'REQUESTS_CA_BUNDLE':'/bad', 'GRPC_DEFAULT_SSL_ROOTS_FILE_PATH':'/bad', 'HTTPS_PROXY':'http://bad'})
                for key in ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'):
                    self.assertEqual(env[key], str(bundle))
                self.assertNotIn('SSL_CERT_DIR', env)
                self.assertNotIn('HTTPS_PROXY', env)
            self.assertEqual(validate.call_count, 2)
    def test_real_system_ca_bundle_when_available(self):
        import ssl
        bundle = ssl.get_default_verify_paths().cafile
        if not bundle or not Path(bundle).is_file(): self.skipTest('no system PEM bundle')
        self.data['analytics']['ca_bundle_file'] = bundle; self.save()
        _, env = self.launch('analytics')
        self.assertEqual(env['REQUESTS_CA_BUNDLE'], bundle)

    def test_invalid_ca_fails_closed(self):
        for path in ('relative.pem', str(self.root/'missing.pem'), str(self.root)):
            self.data['analytics']['ca_bundle_file'] = path; self.save()
            with self.assertRaises(ValueError): self.launch('analytics')
        bundle=self.root/'invalid.pem'; bundle.write_text('not a certificate')
        self.data['analytics']['ca_bundle_file']=str(bundle); self.save()
        with self.assertRaisesRegex(ValueError, 'PEM'): self.launch('analytics')
    def test_unset_ca_does_not_inherit_grpc_requests_or_proxy(self):
        _, env = self.launch('ads', {'GRPC_DEFAULT_SSL_ROOTS_FILE_PATH':'/bad', 'REQUESTS_CA_BUNDLE':'/bad', 'HTTPS_PROXY':'http://bad'})
        self.assertNotIn('GRPC_DEFAULT_SSL_ROOTS_FILE_PATH', env)
        self.assertNotIn('REQUESTS_CA_BUNDLE', env)
        self.assertNotIn('HTTPS_PROXY', env)

    def test_missing_and_world_readable_credentials_fail_closed(self):
        self.creds.chmod(0o644)
        if os.name=='posix':
            with self.assertRaisesRegex(ValueError,'group or other'):self.launch('analytics')
        self.creds.unlink()
        with self.assertRaisesRegex(ValueError,'unavailable'):self.launch('analytics')
    def test_profile_paths_and_unknown_settings_are_rejected(self):
        self.data['analytics']['credentials_file']='relative.json';self.save()
        with self.assertRaisesRegex(ValueError,'absolute'):self.launch('analytics')
        self.data['analytics']={'credentials_file':str(self.creds),'allow_write':True};self.save()
        with self.assertRaisesRegex(ValueError,'unsupported'):self.launch('analytics')
    def test_tampered_config_fails_closed(self):
        wrong=self.root/'config.yaml';wrong.write_text('namespaces:\n  assets: true\n')
        with patch.object(launch,'READ_ONLY_PATH',wrong):
            with self.assertRaisesRegex(ValueError,'integrity'):self.launch('ads')
    def test_version_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'exactly'):launch.launch_spec(str(self.profile),'ads',environ={},get_version=lambda _: '9.9.9')
    def test_credential_file_type_and_symlink_validation(self):
        self.creds.write_text('{}')
        with self.assertRaisesRegex(ValueError,'unsupported'):self.launch('analytics')
        self.creds.write_text(json.dumps({'type':'authorized_user'}));link=self.root/'link.json';link.symlink_to(self.creds)
        self.data['analytics']['credentials_file']=str(link);self.save()
        with self.assertRaisesRegex(ValueError,'symlink'):self.launch('analytics')
    def test_analytics_and_ads_can_use_distinct_credentials(self):
        second=self.root/'ads.json';second.write_text(json.dumps({'type':'service_account'}));second.chmod(0o600)
        self.data['ads']['credentials_file']=str(second);self.save()
        _,analytics=self.launch('analytics');_,ads=self.launch('ads')
        self.assertEqual(analytics['GOOGLE_APPLICATION_CREDENTIALS'],str(self.creds));self.assertEqual(ads['GOOGLE_APPLICATION_CREDENTIALS'],str(second))
        self.assertNotIn('GOOGLE_ADS_DEVELOPER_TOKEN',analytics)

if __name__=='__main__':unittest.main()

class ClientConfigTests(LaunchTests):
    def test_generator_returns_two_readonly_entries_without_token(self):
        from integrations.client_config import client_config
        config=client_config(str(self.profile),__import__('sys').executable)
        self.assertEqual(set(config['mcpServers']),{'flai-analytics-readonly','flai-ads-readonly'})
        self.assertNotIn('dummy_token_value',json.dumps(config))
        self.assertEqual(config['mcpServers']['flai-ads-readonly']['args'][-1],'ads')
    def test_generator_rejects_relative_python_and_wrong_profile(self):
        from integrations.client_config import client_config
        with self.assertRaisesRegex(ValueError,'absolute'):client_config(str(self.profile),'python')
        self.data['ads']['credentials_file']='relative';self.save()
        with self.assertRaisesRegex(ValueError,'absolute'):client_config(str(self.profile),__import__('sys').executable)

@unittest.skipUnless(os.environ.get('FLAI_MCP_TEST_SERVER') in ('ads','analytics','both'), 'explicit upstream handshake test not requested')
class UpstreamHandshakeTests(unittest.IsolatedAsyncioTestCase):
    async def test_official_stdio_tools_are_read_only(self):
        # This exercises only initialize and tools/list with synthetic credentials.
        # It does not invoke a Google reporting API or mutate any external state.
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        import asyncio
        selected=os.environ['FLAI_MCP_TEST_SERVER']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); creds=root/'credentials.json'
            creds.write_text(json.dumps({'type':'authorized_user','client_id':'fake','client_secret':'fake','refresh_token':'fake'}));creds.chmod(0o600)
            profile=root/'profile.json';profile.write_text(json.dumps({'analytics':{'credentials_file':str(creds)},'ads':{'credentials_file':str(creds)}}));profile.chmod(0o600)
            for server in (('analytics','ads') if selected=='both' else (selected,)):
                with self.subTest(server=server):
                    params=StdioServerParameters(command=__import__('sys').executable,args=['-m','integrations.launch','--profile',str(profile),'--server',server],cwd=str(Path(__file__).resolve().parents[1]),env={'PATH':os.environ.get('PATH','/usr/bin'),'HOME':str(root),'ANALYTICS_MCP_ALLOW_WRITE':'true','GOOGLE_ADS_MCP_OAUTH_CLIENT_ID':'ignore','GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET':'ignore'})
                    async with asyncio.timeout(60):
                        async with stdio_client(params) as (reader,writer):
                            async with ClientSession(reader,writer) as session:
                                await session.initialize(); response=await session.list_tools()
                                names={t.name for t in response.tools}
                                self.assertTrue(names, 'upstream server must expose read-only tools')
                                if server=='ads':
                                    self.assertIn('search_search',names)
                                    self.assertIn('customers_list_accessible_customers',names)
                                    self.assertFalse(any(name.startswith(('assets_','labels_')) for name in names),names)
                                else:
                                    self.assertIn('run_report',names)
                                    self.assertFalse(any(name.startswith(('create_','delete_','update_')) for name in names),names)


class TLSDiagnosticTests(LaunchTests):
    def test_probe_does_not_receive_credentials_or_token(self):
        from integrations import tls_diagnostic
        from types import SimpleNamespace
        argv = ['tls_diagnostic', '--profile', str(self.profile), '--server', 'ads']
        with patch('sys.argv', argv), patch('importlib.metadata.version', side_effect=self.version), patch('subprocess.run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(tls_diagnostic.main(), 0)
        command = run.call_args.args[0]
        env = run.call_args.kwargs['env']
        self.assertIn('-I', command)
        self.assertNotIn('GOOGLE_APPLICATION_CREDENTIALS', env)
        self.assertNotIn('GOOGLE_ADS_DEVELOPER_TOKEN', env)
        self.assertNotIn('GOOGLE_ADS_LOGIN_CUSTOMER_ID', env)


class PluginSyncTests(unittest.TestCase):
    def test_tls_launcher_and_probe_match_plugin(self):
        root = Path(__file__).resolve().parents[1]
        for filename in ('launch.py', 'tls_diagnostic.py'):
            self.assertEqual((root/'integrations'/filename).read_bytes(), (root/'plugins/flai-google/integrations'/filename).read_bytes())
