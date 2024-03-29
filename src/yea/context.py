"""yea context."""

import datetime
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from yea import cli, config, plugins, ytest


def _get_width() -> int:
    term = shutil.get_terminal_size(fallback=(60, 12))
    return term[0]


class YeaContext:
    def __init__(self, *, args: "cli.CliArgs"):
        self._args = args
        self._cachedir: Path
        self._covfile: Optional[str] = None
        self._now = datetime.datetime.now()
        self._ts = self._now.strftime("%Y%m%dT%H%M%S")
        self._pid = os.getpid()
        self._setup_env()
        self._cfg = config.Config()
        self._setup_cachedir()
        self._setup_logging()
        self._plugs: plugins.Plugins = plugins.Plugins(yc=self)
        self._platform = self._get_platform()

    def _setup_env(self) -> None:
        self._covfile = os.environ.get("COVERAGE_FILE")

    def _setup_cachedir(self) -> None:
        root = self._cfg._cfroot
        if root is None:
            raise RuntimeError("No config root.")
        p = root.joinpath(".yea_cache")
        if not p.exists():
            p.mkdir()
        self._cachedir = p

    def _setup_logging(self) -> None:
        logger = logging.getLogger("yea")
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logfname = f"debug-{self._ts}-{self._pid}.log"
        lf = self._cachedir.joinpath(logfname)
        fh = logging.FileHandler(lf)
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)
        logger.info("started")

    def _get_platform(self) -> str:
        if self._args.platform:
            return self._args.platform
        p = sys.platform
        if p.startswith("win"):
            p = "win"
        elif p == "darwin":
            p = "mac"
        return p

    def is_live(self) -> bool:
        return self._args.live

    def monitors_inform(self, tlist: list) -> None:
        self._plugs.monitors_inform(tlist)

    def monitors_init(self) -> None:
        self._plugs.monitors_init()

    def monitors_start(self) -> None:
        self._plugs.monitors_start()

    def monitors_start_test(self, yt: "ytest.YeaTest") -> None:
        self._plugs.monitors_start_test(yt)

    def monitors_stop(self) -> None:
        self._plugs.monitors_stop()

    def monitors_reset(self) -> None:
        self._plugs.monitors_reset()

    def test_prep(self, yt: "ytest.YeaTest") -> None:
        width = _get_width()
        print("-" * width)
        print(f"Test: {yt.test_id}")
        print("-" * width)
        # wandb_dir_safe_cleanup()
        self._plugs.test_prep(yt)

    def test_done(self, yt: "ytest.YeaTest") -> None:
        # wandb_dir_safe_cleanup()
        self._plugs.test_done(yt)
        width = _get_width()
        print("-" * width)
        print()

    def test_check(self, yt: "ytest.YeaTest") -> list:
        # ctx = self._backend.get_state()
        result_list = self._plugs.test_check(yt)
        return result_list
