"""Command line entrypoint."""

import argparse
import sys
from typing import Callable, List, Optional

from yea import __version__, context, registry, runner, ytest

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


class CliArgs:
    """Typed command line arguments."""

    plugin_args: List[str]

    def __init__(self, args: argparse.Namespace):
        self.action: Literal["run", "list", "r", "l"] = args.action
        self.all: bool = args.all
        self.debug: bool = args.debug
        self.yeadoc: bool = args.yeadoc
        self.dryrun: bool = args.dryrun
        self.func: Callable = args.func
        self.live: bool = args.live
        self.mitm: bool = args.mitm
        self.noskip: bool = args.noskip
        self.platform: Optional[str] = args.platform
        self.shard: Optional[str] = args.shard
        self.suite: Optional[str] = args.suite
        self.tests: Optional[List[str]] = args.tests
        self.plugin_args: list = args.plugin_args or []
        self.strict: bool = args.strict
        self.splits: Optional[int] = args.splits
        self.group: Optional[int] = args.group
        self.store_durations: bool = args.store_durations


def get_tests(yc: "context.YeaContext") -> List["ytest.YeaTest"]:
    test_reg = registry.Registry(yc=yc)
    test_reg.probe(all_tests=yc._args.all, tests=yc._args.tests)
    tests = test_reg.get_tests()
    return tests


def cli_list(yc: "context.YeaContext") -> None:
    tests = get_tests(yc)
    test_ids = [len(t.test_id) for t in tests if t.test_id is not None]
    if None in test_ids:
        raise ValueError("Test ids must be set.")
    tlen = max(test_ids) if test_ids else 0

    print("Tests:")
    for t in tests:
        print("  {:<{}s}: {}".format(t.test_id, tlen, t.name))


def cli_run(yc: "context.YeaContext") -> None:
    tests = get_tests(yc)
    tr = runner.TestRunner(yc=yc)

    if yc._args.yeadoc:
        tr.yeadoc_prepare(tests)

    tr.run(tests)


def cli() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)

    subparsers = parser.add_subparsers(dest="action", title="action", description="Action to perform")
    parser.add_argument("--debug", action="store_true", help="Print out extra debug info")
    parser.add_argument("--yeadoc", help="scan for docstring tests", action="store_true")
    parser.add_argument("--dryrun", action="store_true", help="Do not do anything")
    parser.add_argument("--live", action="store_true", help="Run against real server")
    parser.add_argument("--mitm", action="store_true", help="Run against mitm server")
    parser.add_argument("--strict", action="store_true", help="Fail if something happens")
    parser.add_argument("--shard", help="Specify testing shard")
    parser.add_argument("--suite", help="Specify testing suite")
    parser.add_argument("--platform", help="Specify testing platform")
    parser.add_argument("--noskip", action="store_true", help="Do not skip any tests")
    parser.add_argument("-p", "--plugin-args", action="append", help="Add plugin args")
    parser.add_argument("--version", help="Print version and exit", action="store_true")
    # for split tests (follows pytest-split conventions)
    parser.add_argument("--splits", type=int, help="Number of split workers")
    parser.add_argument("--group", type=int, help="Which split worker are we")
    parser.add_argument("--store-durations", action="store_true", help="Store split worker test info")

    parse_list = subparsers.add_parser("list", aliases=["l"], allow_abbrev=False)
    parse_list.add_argument("-a", "--all", action="store_true", help="List all")
    parse_list.add_argument("tests", nargs="*")
    parse_list.set_defaults(func=cli_list)

    parse_run = subparsers.add_parser("run", aliases=["r"], allow_abbrev=False)
    parse_run.add_argument("-a", "--all", action="store_true", help="Run all")
    parse_run.add_argument("tests", nargs="*")
    parse_run.set_defaults(func=cli_run)

    args = parser.parse_args()

    if args.version:
        print(f"Yea {__version__}")
        sys.exit(0)

    if not args.action:
        parser.print_help()
        sys.exit(1)

    cli_args = CliArgs(args)
    yc = context.YeaContext(args=cli_args)
    args.func(yc)


if __name__ == "__main__":
    cli()
