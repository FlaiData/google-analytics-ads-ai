"""Unauthenticated TLS probes under the MCP launcher's sanitized environment."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import os
import subprocess
import sys


def probe():
    # No credentials, account data or tokens are used in these connectivity checks.
    import requests
    import grpc
    try:
        response = requests.get('https://oauth2.googleapis.com/.well-known/openid-configuration', timeout=10, allow_redirects=False)
        print(f'OAuth HTTPS: TLS connected; HTTP status {response.status_code}')
    except requests.exceptions.SSLError:
        print('OAuth HTTPS: TLS verification failed')
    except requests.exceptions.RequestException as exc:
        print(f'OAuth HTTPS: connection failed ({type(exc).__name__})')
    for host in ('analyticsdata.googleapis.com', 'googleads.googleapis.com'):
        channel = grpc.secure_channel(f'{host}:443', grpc.ssl_channel_credentials())
        try:
            grpc.channel_ready_future(channel).result(timeout=10)
            print(f'gRPC {host}: TLS channel ready')
        except grpc.FutureTimeoutError:
            print(f'gRPC {host}: channel not ready (TLS, DNS, proxy, firewall or other network issue)')
        finally:
            channel.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--server', choices=('analytics', 'ads'), required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("flai_launch", Path(__file__).with_name("launch.py"))
    launch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launch)
    try:
        _, env = launch.launch_spec(args.profile, args.server)
        # Never pass credentials or developer token to probes.
        for key in ('GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_ADS_DEVELOPER_TOKEN', 'GOOGLE_ADS_LOGIN_CUSTOMER_ID'):
            env.pop(key, None)
        print('Using explicit profile CA bundle:', 'yes' if 'REQUESTS_CA_BUNDLE' in env else 'no (runtime defaults)')
        print('Proxy variables are excluded by the launcher. No account API calls are made.', flush=True)
        # Same interpreter and isolated mode as the MCP child, with the launcher environment.
        completed = subprocess.run([sys.executable, '-I', str(Path(__file__).resolve()), '--probe'], env=env, timeout=40, check=False)
        return completed.returncode
    except (ValueError, OSError, subprocess.TimeoutExpired):
        print('Diagnostic could not start; verify the profile, installed packages and network.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    if sys.argv[1:] == ['--probe']:
        probe()
    else:
        raise SystemExit(main())
