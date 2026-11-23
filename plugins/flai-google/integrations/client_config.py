"""Generate client configuration for the two official read-only MCP launchers."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
from .launch import UPSTREAM, launch_spec


def client_config(profile_path, python_path):
    if not isinstance(python_path,str) or not Path(python_path).is_absolute():
        raise ValueError('Python interpreter must be an absolute path')
    if not Path(python_path).is_file() or not os.access(python_path,os.X_OK):
        raise ValueError('Python interpreter must be an executable regular file')
    # Validate each profile without exposing credential contents in the result.
    # The selected interpreter validates installed package versions at launch.
    for server in ('analytics','ads'):
        launch_spec(profile_path,server,environ={},get_version=lambda package: dict(UPSTREAM.values())[package])
    def entry(server):
        return {'command':python_path,'args':['-m','integrations.launch','--profile',profile_path,'--server',server]}
    return {'mcpServers':{'flai-analytics-readonly':entry('analytics'),'flai-ads-readonly':entry('ads')}}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',required=True,help='absolute path to the private profile JSON')
    parser.add_argument('--python',required=True,help='absolute path to the selected virtualenv Python interpreter')
    args=parser.parse_args(argv)
    try:
        result=client_config(args.profile,args.python)
    except (ValueError,OSError) as exc:
        print('MCP client configuration refused:',exc,file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())
