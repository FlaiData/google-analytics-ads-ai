"""Run a single validated Google Ads label CREATE in an interactive terminal."""
import argparse
import asyncio
import hmac
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from integrations.launch import _json_file, _private_file, launch_spec

CONFIG = b'namespaces:\n  labels:\n    enabled: true\n    enabled_tools:\n      - manage_labels: true\n'
TOOL = 'labels_manage_labels'


def read_plan(path):
    plan = _json_file(_private_file(path, 'plan'), 'plan')
    if set(plan) - {'customer_id', 'name', 'description', 'background_color'} or not {'customer_id', 'name'} <= set(plan):
        raise ValueError('plan must contain customer_id and name and only supported fields')
    if not isinstance(plan['customer_id'], str) or not re.fullmatch(r'[0-9]{10}', plan['customer_id']):
        raise ValueError('customer_id must contain exactly 10 digits')
    for key, limit in [('name', 255), ('description', 200)]:
        if key in plan:
            value = plan[key]
            if not isinstance(value, str) or not value.strip() or len(value) > limit or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
                raise ValueError(f'invalid {key}')
    if 'background_color' in plan and (not isinstance(plan['background_color'], str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', plan['background_color'])):
        raise ValueError('background_color must be a #RRGGBB color')
    return dict(plan)


def make_spec(profile):
    data = _json_file(_private_file(profile, 'profile'), 'profile')
    ads = data.get('ads')
    if not isinstance(ads, dict):
        raise ValueError('profile requires an ads section')
    cred = _json_file(_private_file(ads.get('credentials_file'), 'credentials file'), 'credentials file')
    if cred.get('type') != 'authorized_user':
        raise ValueError('manual changes require authorized_user credentials')
    command, env = launch_spec(profile, 'ads')
    return command, env


def check_config(path):
    if path.is_symlink() or path.read_bytes() != CONFIG or (os.name == 'posix' and path.stat().st_mode & 0o222):
        raise ValueError('manual MCP configuration integrity check failed')


def decode(result):
    if result.isError:
        raise ValueError('MCP tool reported an error')
    content = result.content
    if len(content) != 1 or getattr(content[0], 'type', None) != 'text':
        raise ValueError('unexpected MCP response')
    return content[0].text


def verify_proposal(proposal, args, compute_checksum):
    if not isinstance(proposal, dict) or proposal.get('status') != 'PROPOSED' or proposal.get('validate_only') is not True or proposal.get('customer_id') != args['customer_id']:
        raise ValueError('invalid validation proposal')
    payload = {'tool': 'manage_labels', 'operation': 'CREATE', 'name': args['name'], 'background_color': args.get('background_color'), 'description': args.get('description'), 'label_id': None}
    checksum = proposal.get('checksum')
    if not isinstance(checksum, str) or not re.fullmatch(r'[0-9a-f]{64}', checksum) or not hmac.compare_digest(checksum, compute_checksum(args['customer_id'], payload)):
        raise ValueError('proposal checksum mismatch')
    fields = {'Name': args['name']}
    for source, target in [('description', 'Description'), ('background_color', 'Background Color')]:
        if source in args:
            fields[target] = args[source]
    items = proposal.get('change_items')
    if not isinstance(items, list) or len(items) != len(fields):
        raise ValueError('proposal fields mismatch')
    for item in items:
        if not isinstance(item, dict) or item.get('operation') != 'CREATE' or item.get('entity_readable') != 'Label' or item.get('primary_key_readable') != args['name'] or fields.pop(item.get('field_readable'), None) != item.get('value_readable'):
            raise ValueError('proposal fields mismatch')
    if fields:
        raise ValueError('proposal fields mismatch')
    return checksum


async def perform(session, plan, login_id, compute_checksum, read_input, emit, check_integrity):
    # Construct a fresh fixed snapshot; no input or plan reload occurs between calls.
    args = {'customer_id': plan['customer_id'], 'operation': 'CREATE', 'name': plan['name']}
    for key in ('background_color', 'description'):
        if key in plan:
            args[key] = plan[key]
    if login_id:
        args['login_customer_id'] = login_id
    check_integrity()
    response = await session.call_tool(TOOL, arguments={**args, 'validate_only': True})
    try:
        proposal = json.loads(decode(response))
    except (ValueError, TypeError) as exc:
        raise ValueError('validation did not return a valid proposal') from exc
    checksum = verify_proposal(proposal, args, compute_checksum)
    emit(json.dumps({'parameters': args, 'proposal': proposal}, indent=2, ensure_ascii=True))
    answer = read_input(f'Type APPROVE {args["customer_id"]} {checksum} to create this label: ')
    if not hmac.compare_digest(answer, f'APPROVE {args["customer_id"]} {checksum}'):
        raise ValueError('approval did not match; no write attempted')
    check_integrity()
    # No retries, including transport errors and tool errors: outcome can be unknown.
    try:
        response = await session.call_tool(TOOL, arguments={**args, 'validate_only': False, 'checksum': checksum})
        result = decode(response)
    except Exception as exc:
        raise RuntimeError('commit outcome unknown; inspect Google Ads before any new attempt') from exc
    emit('Commit response: ' + json.dumps(result, ensure_ascii=True))


async def run(profile, plan):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from ads_mcp.propose_and_confirm import compute_checksum

    command, env = make_spec(profile)
    with tempfile.TemporaryDirectory(prefix='ads-label-') as temp:
        path = Path(temp) / 'tools.yaml'
        path.write_bytes(CONFIG)
        path.chmod(0o400)
        check_config(path)
        env['GOOGLE_ADS_MCP_TOOLS_CONFIG'] = str(path)
        server = StdioServerParameters(command=command[0], args=command[1:], env=env)
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                if getattr(tools, 'nextCursor', None) or {tool.name for tool in tools.tools} != {TOOL}:
                    raise ValueError('manual server did not expose exactly the expected tool')
                await perform(session, plan, env.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID'), compute_checksum, input, print, lambda: check_config(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, help='absolute path to private profile JSON')
    parser.add_argument('--plan', required=True, help='absolute path to private label plan JSON')
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print('Interactive stdin and stdout TTY required; no action taken.', file=sys.stderr)
        return 1
    try:
        plan = read_plan(args.plan)
        asyncio.run(run(args.profile, plan))
    except (KeyboardInterrupt, EOFError):
        print('Interrupted. If commit had begun, outcome is unknown; inspect Google Ads.', file=sys.stderr)
        return 1
    except Exception as exc:
        # Avoid printing upstream exceptions that may include sensitive values.
        if isinstance(exc, (ValueError, RuntimeError)) and str(exc) in {'approval did not match; no write attempted', 'commit outcome unknown; inspect Google Ads before any new attempt'}:
            print(str(exc), file=sys.stderr)
        else:
            print('Operation refused or failed. If commit had begun, inspect Google Ads before retrying.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
