"""Launch pinned official Google MCP servers in isolated read-only stdio mode.

Profiles are local files outside the repository. No credentials are printed.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys

UPSTREAM = {'analytics': ('analytics-mcp', '1.1.0'), 'ads': ('google-ads-mcp', '0.0.6')}
READ_ONLY_CONFIG = b'namespaces:\n  customers: true\n  search: true\n  metadata: true\n  labels: false\n  assets: false\n'
READ_ONLY_PATH = Path(__file__).resolve().with_name('ads_readonly.yaml')
CREDENTIAL_TYPES = frozenset({'authorized_user', 'service_account', 'external_account', 'impersonated_service_account'})
SAFE_ENV = ('PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'LC_CTYPE', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'SYSTEMROOT', 'WINDIR')


def _private_file(value, label):
    if not isinstance(value, str) or not value or not Path(value).is_absolute():
        raise ValueError(f'{label} must be an absolute file path')
    path = Path(value)
    if path.is_symlink():
        raise ValueError(f'{label} must not be a symlink')
    try:
        details = path.stat()
    except OSError as exc:
        raise ValueError(f'{label} is unavailable') from exc
    if not stat.S_ISREG(details.st_mode):
        raise ValueError(f'{label} must be a regular file')
    if os.name == 'posix' and details.st_mode & 0o077:
        raise ValueError(f'{label} must not be accessible to group or other users (use chmod 600)')
    return path


def _ca_bundle(value):
    # CA certificates are public trust material, so unlike credentials the file
    # may be system-owned and world-readable. Only explicitly selected files
    # are used; symlinks are useful for system-managed trust stores.
    if not isinstance(value, str) or not Path(value).is_absolute():
        raise ValueError('ca_bundle_file must be an absolute file path')
    path = Path(value)
    try:
        if not path.is_file():
            raise ValueError('ca_bundle_file must be a regular file')
        ssl.create_default_context(cafile=str(path))
    except (OSError, ssl.SSLError) as exc:
        raise ValueError('ca_bundle_file must be a readable PEM certificate bundle') from exc
    return str(path)


def _json_file(path, label):
    try:
        with path.open(encoding='utf-8') as f:
            value = json.load(f)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'{label} must be a readable JSON object') from exc
    if not isinstance(value, dict):
        raise ValueError(f'{label} must be a JSON object')
    return value


def _optional_text(settings, key, regex):
    val = settings.get(key)
    if val is None:
        return None
    if not isinstance(val, str) or not re.fullmatch(regex, val):
        raise ValueError(f'invalid {key}')
    return val


def launch_spec(profile_path, server, *, environ=None, get_version=importlib.metadata.version):
    """Return isolated argv/env. Callers must not log the env or profile contents."""
    if server not in UPSTREAM:
        raise ValueError('server must be analytics or ads')
    profile = _json_file(_private_file(profile_path, 'profile'), 'profile')
    if set(profile) - {'analytics', 'ads'}:
        raise ValueError('profile contains unsupported sections')
    section = profile.get(server)
    if not isinstance(section, dict):
        raise ValueError(f'profile is missing the {server} section')
    allowed = {'credentials_file', 'cloud_project', 'ca_bundle_file'}
    if server == 'ads':
        allowed |= {'developer_token_file', 'login_customer_id'}
    if set(section) - allowed:
        raise ValueError('profile section contains unsupported settings')
    credentials_path = _private_file(section.get('credentials_file'), 'credentials file')
    credentials = _json_file(credentials_path, 'credentials file')
    if credentials.get('type') not in CREDENTIAL_TYPES:
        raise ValueError('unsupported Google credential type')
    project = _optional_text(section, 'cloud_project', r'[a-z][a-z0-9-]{4,28}[a-z0-9]')
    source_env = os.environ if environ is None else environ
    env = {k: source_env[k] for k in SAFE_ENV if k in source_env}
    env['GOOGLE_APPLICATION_CREDENTIALS'] = str(credentials_path)
    if 'ca_bundle_file' in section:
        ca = _ca_bundle(section['ca_bundle_file'])
        env.pop('SSL_CERT_DIR', None)
        # requests/OAuth, Python SSL, and gRPC have separate trust configuration.
        env.update(SSL_CERT_FILE=ca, REQUESTS_CA_BUNDLE=ca, GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=ca)
    if project:
        env['GOOGLE_CLOUD_PROJECT'] = project
    if server == 'analytics':
        # The upstream CLI has no --no-allow-write flag; override inherited env.
        env['ANALYTICS_MCP_ALLOW_WRITE'] = 'false'
        env['ANALYTICS_MCP_OAUTH'] = 'false'
        code = 'from analytics_mcp.server import run_server; run_server()'
    else:
        login = _optional_text(section, 'login_customer_id', r'[0-9]{10}')
        if login:
            env['GOOGLE_ADS_LOGIN_CUSTOMER_ID'] = login
        if 'developer_token_file' in section:
            token_path = _private_file(section['developer_token_file'], 'developer token file')
            try:
                token = token_path.read_text(encoding='utf-8').strip()
            except (OSError, UnicodeError) as exc:
                raise ValueError('developer token file is unreadable') from exc
            if not re.fullmatch(r'[A-Za-z0-9_-]{10,256}', token):
                raise ValueError('developer token file has an invalid value')
            env['GOOGLE_ADS_DEVELOPER_TOKEN'] = token
        try:
            if READ_ONLY_PATH.is_symlink() or READ_ONLY_PATH.read_bytes() != READ_ONLY_CONFIG:
                raise ValueError('read-only Ads configuration integrity check failed')
        except OSError as exc:
            raise ValueError('read-only Ads configuration is missing') from exc
        env['GOOGLE_ADS_MCP_TOOLS_CONFIG'] = str(READ_ONLY_PATH)
        code = 'from ads_mcp.server import run_server; run_server()'
    package, expected = UPSTREAM[server]
    try:
        actual = get_version(package)
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError(f'install {package}=={expected} in this Python environment') from exc
    if actual != expected:
        raise ValueError(f'{package} must be exactly {expected}; review newer versions before use')
    # -I excludes cwd and PYTHONPATH from import resolution; stdout is reserved for MCP.
    return [sys.executable, '-I', '-c', code], env


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, help='absolute path to a private JSON profile')
    parser.add_argument('--server', required=True, choices=sorted(UPSTREAM))
    args = parser.parse_args(argv)
    try:
        command, env = launch_spec(args.profile, args.server)
        os.execve(command[0], command, env)
    except (ValueError, OSError) as exc:
        print(f'MCP launch refused: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
