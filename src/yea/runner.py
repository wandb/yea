"""test runner."""

import pathlib
import sys

from yea import ytest


class TestRunner:
    def __init__(self, *, yc):
        self._yc = yc
        self._cfg = yc._cfg
        self._args = yc._args
        self._test_files = []
        self._results = {}
        self._test_list = []
        self._populate()

    def _populate(self):
        tpaths = []
        # TODO: clean up args parsing
        args_tests = getattr(self._args, "tests", None)
        if getattr(self._args, "all", None):
            args_tests = None
        for tdir in self._cfg.test_dirs:
            path_dir = pathlib.Path(self._cfg.test_root, tdir)
            for tpath in path_dir.glob("t_[0-9-]*_*.py"):
                if args_tests is not None and tpath.name not in args_tests:
                    continue
                tpaths.append(tpath)
        tlist = []
        for tname in sorted(tpaths):
            t = ytest.YeaTest(tname=tname, yc=self._yc)
            tlist.append(t)
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
