"""Config class."""

import configparser
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def _load_config(cfpath: Path) -> configparser.ConfigParser:
    if cfpath is None:
        raise ValueError("No config file found")
    cf = configparser.ConfigParser()
    cf.read(cfpath)
    return cf


def _find_config(root: bool = False) -> Optional[Path]:
    """Return path to the root yea config."""
    possible_root_cf = None
    cwd = Path.cwd()

    # Walk directories all the way looking for config files
    for p in [cwd] + list(cwd.parents):
        cf = Path(p, ".yearc")
        if cf.is_file():
            cp = _load_config(cf)
            if cp.getboolean("yea", "root", fallback=False) == root:
                return cf
            # save that this is the possible root config
            possible_root_cf = cf

        # if we are at the top of a git tree, dont search any farther
        gd = Path(p, ".git")
        if gd.is_dir():
            break

    # if we walked all parents and didnt find a root, assume the lowest is root
    if possible_root_cf:
        return possible_root_cf

    return None


class Config:
    _cfroot: Path
    _test_dirs: List[str]
    _yeadoc_dirs: List[str]
    _results_file: Optional[str]

    def __init__(self) -> None:
        self._coverage_config_template: Optional[str] = None
        self._coverage_source: Optional[str] = None
        self._coverage_source_env: Optional[str] = None
        self._coverage_run_in_process: bool = True
        self._test_dirs = []
        self._yeadoc_dirs = []
        self._results_file = None
        found = _find_config(root=True)
        if found:
            cf = _load_config(found)
            self._cfroot = found.parent
            self._parse_config(cf)
        else:
            self._cfroot = Path(".")
            self._test_dirs = ["."]

    def _parse_config(self, cf: configparser.ConfigParser) -> List[str]:
        ycfg = cf.items("yea")
        ydict = dict(ycfg)
        test_paths = ydict.get("test_paths", "")
        test_list = re.findall(r"[\S]+", test_paths)
        self._test_dirs = test_list

        yeadoc_paths = ydict.get("yeadoc_paths", "")
        yeadoc_list = re.findall(r"[\S]+", yeadoc_paths)
        self._yeadoc_dirs = yeadoc_list

        self._coverage_config_template = ydict.get("coverage_config_template", "")
        self._coverage_source = ydict.get("coverage_source")
        # TODO: clean up how this works, user could already have an absolute path
        if self._coverage_source and self.test_root:
            self._coverage_source = os.path.join(self.test_root, self._coverage_source)
        self._coverage_source_env = ydict.get("coverage_source_env")
        coverage_run_in_process = ydict.get("coverage_run_in_process")
        if coverage_run_in_process is not None:
            self._coverage_run_in_process = coverage_run_in_process.lower() == "true"
        self._results_file = ydict.get("results_file")

        return test_list

    @property
    def test_dirs(self) -> List[str]:
        return self._test_dirs

    @property
    def yeadoc_dirs(self) -> List[str]:
        return self._yeadoc_dirs

    @property
    def test_root(self) -> Optional[Path]:
        return self._cfroot

    @property
    def durations_path(self) -> Optional[Path]:
        path = self.test_root
        if path is None:
            return None
        # TODO: support specifying in config eventually
        path = Path.joinpath(path, ".yea_durations")
        return path
