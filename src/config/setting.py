import argparse

from typing import List
from dataclasses import fields, MISSING

from src import __description__
from src.app_types import params

type_map = {
    'list': lambda x: x.split(",")
}

class CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def add_argument(self, action):
        if action.type and action.metavar is None:
            action.metavar = getattr(action.type, '__name__', str(action.type))
        super().add_argument(action)

def parse_args(description="") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=CustomHelpFormatter
    )
    for f in fields(params.AllParams):
        arg_type = f.type
        default = f.default_factory if f.default_factory is not MISSING else f.default
        nargs = f.metadata.get("nargs", None)
        help_info = f.metadata.get("help", "")
        arg_name = f"--{f.name.replace('_', '-')}" if not nargs else f.name
        if arg_type == bool:
            parser.add_argument(
                arg_name,
                action=argparse.BooleanOptionalAction,
                help=help_info,
                default=default
            )
        else:
            if arg_type == List[str]:    
                arg_type = type_map.get('list', str)
            parser.add_argument(
                arg_name,
                nargs=nargs,
                type=arg_type,
                help=help_info,
                default=default
            )
    return parser

def get_config() -> params.AllParams:
    '''取得設定'''
    parser = parse_args(__description__)
    args, unknown_args  = parser.parse_known_args()
    config = params.AllParams(**vars(args))
    return config
