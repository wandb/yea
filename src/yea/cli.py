"""Command line entrypoint."""

import argparse
import sys

from yea import context, runner


def cli_list(yc):
    print("Tests:")
    yc._args.action = "list"
    tr = runner.TestRunner(yc=yc)
    tests = tr.get_tests()
    for t in tests:
        print("  ", t.test_id, ":", t.name)


def cli_run(yc):
    yc._args.action = "run"
    tr = runner.TestRunner(yc=yc)
    tr.run()


def cli():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="action", title="action", description="Action to perform"
    )
    parser.add_argument("--dryrun", action="store_true", help="Dont do anything")
    parser.add_argument("--live", action="store_true", help="Run against real server")

    parse_list = subparsers.add_parser("list", aliases=["l"])
    parse_list.set_defaults(func=cli_list)
    parse_list.add_argument("tests", nargs="*")

    parse_run = subparsers.add_parser("run", aliases=["r"])
    parse_run.add_argument("--all", action="store_true", help="Run all")
    parse_run.add_argument("tests", nargs="*")
    parse_run.set_defaults(func=cli_run)
    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    yc = context.YeaContext(args=args)
    args.func(yc)
