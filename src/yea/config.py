"""Config class."""

import configparser
from pathlib import Path
import re


class Config:
    def __init__(self):
        self._cfname = None
        self._cfroot = None
        self._cf = None
        self._test_dirs = []
        found = self._find_config()
        assert found
        cf = self._load_config(self._cfname)
        self._parse_config(cf)
        self._cf = cf

    def _find_config(self) -> Path:
        p = Path.cwd()
        while True:
            cf = Path(p, ".yearc")
            if cf.is_file():
                self._cfname = cf
                self._cfroot = p
                return True
            n = p.parent
            if n.samefile(p):
                break
            p = n
        return

    def _load_config(self, p):
        cf = configparser.ConfigParser()
        cf.read(p)
        return cf

    def _parse_config(self, cf):
        ycfg = cf.items("yea")
        ydict = dict(ycfg)
        test_paths = ydict.get("test_paths", "")
        test_list = re.findall(r"[\S]+", test_paths)
        self._test_dirs = test_list
        return test_list

    @property
    def test_dirs(self):
        return self._test_dirs

    @property
    def test_root(self):
        return self._cfroot
