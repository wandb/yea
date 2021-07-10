"""test runner."""

import pathlib
import re
import sys

from yea import testspec, ytest


def convert(text):
    return int(text) if text.isdigit() else text.lower()


def alphanum_sort(key):
    return [convert(c) for c in re.split("([0-9]+)", key._sort_key)]


class TestRunner:
    def __init__(self, *, yc):
        self._yc = yc
        self._cfg = yc._cfg
        self._args = yc._args
        self._test_files = []
        self._results = {}
        self._test_list = []
        self._populate()

    def _get_args_list(self):
        if getattr(self._args, "all", None):
            return None
        # TODO: clean up args parsing
        args_tests = getattr(self._args, "tests", None)
        if not args_tests:
            return None

        alist = []
        for a in args_tests:
            p = pathlib.Path(a)
            p = p.resolve()
            alist.append(str(p))
        return alist

    def _populate(self):
        tpaths = []

        args_tests = self._get_args_list()

        for tdir in self._cfg.test_dirs:
            path_dir = pathlib.Path(self._cfg.test_root, tdir)
            # TODO: look for .yea, or look for .py with docstring
            for tpath in path_dir.glob("*.py"):
                if args_tests is not None and str(tpath) not in args_tests:
                    continue
                docstr = testspec.load_docstring(tpath)
                spec = testspec.load_yaml_from_docstring(docstr)
                if not spec:
                    continue
                tpaths.append(tpath)
            for tpath in path_dir.glob("*.yea"):
                # TODO: parse yea file looking for path info
                py_fname = str(tpath)[:-4] + ".py"
                if args_tests is not None and py_fname not in args_tests:
                    continue
                py_path = pathlib.Path(py_fname)
                tpaths.append(py_path)

        tlist = []
        for tname in tpaths:
            t = ytest.YeaTest(tname=tname, yc=self._yc)
            t._load()
            tlist.append(t)

        tlist.sort(key=alphanum_sort)
        self._test_list = tlist

    def _runall(self):
        for t in self._test_list:
            self._yc.monitors_reset()
            t.run()
            self._capture_result(t)

    def _check_dict(self, result, s, expected, actual):
        if expected is None:
            return
        for k, v in actual.items():
            exp = expected.get(k)
            if exp != v:
                result.append("BAD_{}({}:{}!={})".format(s, k, exp, v))
        for k, v in expected.items():
            act = actual.get(k)
            if v != act:
                result.append("BAD_{}({}:{}!={})".format(s, k, v, act))

    def _capture_result(self, t):
        test_cfg = t._test_cfg
        if not test_cfg:
            return
        if self._yc.is_live():
            # we are live
            return
        result = self._yc.test_check(t)
        print("GOTRES", result)
        result_str = ",".join(result)
        self._results[t._tname] = result_str

    def run(self):
        self._yc.monitors_init()
        try:
            self._yc.monitors_start()
            self._populate()
            self._runall()
            self.finish()
        finally:
            self._yc.monitors_stop()

    def finish(self):
        exit = 0
        r_names = sorted(self._results)
        for k in r_names:
            r = self._results[k]
            print("{}: {}".format(k, r))
            if r:
                exit = 1
        sys.exit(exit)

    def get_tests(self):
        return self._test_list
