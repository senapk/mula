from __future__ import annotations

import argparse
import sys


from .actions import Actions
from .credentials import Credentials
from .moodle_api import MoodleAPI
from .__init__ import __version__


def main():
    # p_config = argparse.ArgumentParser(add_help=False)
    # p_config.add_argument('-c', '--config', type=str, help="config file path")

    p_section = argparse.ArgumentParser(add_help=False)
    p_section.add_argument('-s', '--section', metavar='SECTION', type=int, help="")

    p_selection = argparse.ArgumentParser(add_help=False)
    selection_group = p_selection.add_mutually_exclusive_group()
    selection_group.add_argument('--all', action='store_true', help="All vpls")
    selection_group.add_argument('-i', '--ids', type=int, metavar='ID', nargs='*', action='store')
    selection_group.add_argument('-l', '--labels', type=str, metavar='LABEL', nargs='*', action='store')
    selection_group.add_argument('-s', '--sections', metavar='SECTION', nargs='*', type=int, help="")

    p_common = argparse.ArgumentParser(add_help=False)
    p_common.add_argument('-d', '--duedate', type=str, action='store', 
                           help='duedate 0 to disable or duedate yyyy:m:d:h:m')
    p_common.add_argument('-m', '--maxfiles', type=int, action='store', help='max student files')
    p_common.add_argument('-v', '--visible', type=int, action='store', help="make entry visible 1 or 0")
    p_common.add_argument('-e', '--exec', action='store_true', help="enable all execution options")

    p_out = argparse.ArgumentParser(add_help=False)
    p_out.add_argument('-o', '--output', type=str, default='.', action='store', help='Output directory')

    desc = ("Gerenciar vpls do moodle de forma automatizada")

    parser = argparse.ArgumentParser(prog='mapi.py', description=desc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config', type=str, help="config file path")
    parser.add_argument('-t', '--timeout', type=int, help="max timeout to way moodle response")
    parser.add_argument('-v', '--version', action="store_true", help="show version")
    parser.add_argument('-l', '--local', action="store_true", help="search for mapi.json inside current directory")

    parser.add_argument("--username", "-u", type=str, help='username')
    parser.add_argument("--password", "-p", type=str, help="password")
    parser.add_argument("--index", "-i", type=int, help="Moodle course id")

    subparsers = parser.add_subparsers(title="subcommands", help="help for subcommand")

    parser_add = subparsers.add_parser('add', parents=[p_section, p_common], help="add")
    parser_add.add_argument("--remote", "-r", type=str, help="[fup | ed | poo]")
    parser_add.add_argument('targets', type=str, nargs='+', action='store', help='remote targets')
    parser_add.set_defaults(func=Actions.add)

    parser_list = subparsers.add_parser('list', parents=[p_section], help='list')
    parser_list.add_argument('-u', '--url', action='store_true', help="Show vpl urls")
    parser_list.add_argument("-t", "--topic", action='store_true', help="Show only session topics")
    parser_list.set_defaults(func=Actions.list)

    parser_rm = subparsers.add_parser('rm', parents=[p_selection], help="Remove from Moodle")
    parser_rm.set_defaults(func=Actions.rm)

    parser_down = subparsers.add_parser('down', parents=[p_selection, p_out], help='Download vpls')
    parser_down.set_defaults(func=Actions.down)

    parser_update = subparsers.add_parser('update', parents=[p_selection, p_common], help='Update vpls')
    parser_update.add_argument("--remote", "-r", type=str, help="[fup | ed | poo]")
    parser_update.add_argument('-c', '--content', action='store_true', help="add/update conteúdo da questão")
    parser_update.set_defaults(func=Actions.update)

    args = parser.parse_args()

    if args.version:
        print(__version__)
        sys.exit(0)

    if args.timeout is not None:
        MoodleAPI.default_timeout = args.timeout

    credentials = Credentials.load_credentials()
    if args.config:
        credentials.load_file(args.config)
    if args.username:
        credentials.username = args.username
    if args.password:
        credentials.password = args.password
    if args.index:
        credentials.index = args.index
    # check if remote exists
    # if args.remote:
    #     credentials.remote_db = args.remote
    credentials.fill_empty()

    # verify if any subcommand was used
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
