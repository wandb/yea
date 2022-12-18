"""test runner."""
import json
import logging
import os
import pathlib
import re
import shutil
import sys
from typing import Any, Generator, List, Optional, Union

from yea import context, util, ytest

logger = logging.getLogger(__name__)
junit_xml = util.vendor_import("wandb_junit_xml")


def convert(text: str) -> Union[int, str]:
    return int(text) if text.isdigit() else text.lower()


def alphanum_sort(key: "ytest.YeaTest") -> List[Union[int, str]]:
    return [convert(c) for c in re.split("([0-9]+)", key._sort_key)]


class TestRunner:
    def __init__(self, *, yc: "context.YeaContext"):
        self._yc = yc
        self._cfg = yc._cfg
        if self._cfg.test_root is None:
            raise TypeError("test_root is not set")
        self._tmpdir = pathlib.Path(self._cfg.test_root, ".yeadoc")
        self.prepare()
        self._args = yc._args
        self._test_files: List[str] = []
        # self._results: List[junit_xml.TestCase] = []
        self._results: List = []
        self._test_list: List["ytest.YeaTest"] = []

    def prepare(self) -> None:
        if self._yc._cfg._coverage_run_in_process:
            os.environ["YEA_RUN_COVERAGE"] = str(self._yc._cfg._coverage_run_in_process)
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir)
        self._tmpdir.mkdir()

    def clean(self) -> None:
        os.environ.pop("YEA_RUN_COVERAGE", None)
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir)

    def _get_args_list(self) -> Optional[List[str]]:
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

    def _get_dirs(self) -> Generator[pathlib.Path, None, None]:
        # generate to return all test dirs and recursively found dirs
        if self._cfg.test_root is None:
            raise TypeError("test_root is not set")
        for tdir in self._cfg.test_dirs:
            path_dir = pathlib.Path(self._cfg.test_root, tdir)
            yield path_dir
            for root, dirs, _ in os.walk(path_dir, topdown=True):
                # TODO: temporary hack to avoid walking into wandb dir
                # use .gitignore instead
                if "wandb" in dirs:
                    dirs.remove("wandb")
                if ".tox" in dirs:
                    dirs.remove(".tox")
                for d in dirs:
                    path_dir = pathlib.Path(self._cfg.test_root, root, d)
                    yield path_dir

    def _runall(self) -> None:
        for t in self._test_list:
            self._yc.monitors_reset()
            self._yc.monitors_start_test(t)
            t.run()
            self._capture_result(t)

    def _check_dict(
        self,
        result: List[str],
        s: Any,
        expected: Optional[dict],
        actual: dict,
    ) -> None:
        if expected is None:
            return
        for k, v in actual.items():
            exp = expected.get(k)
            if exp != v:
                result.append(f"BAD_{s}({k}:{exp}!={v})")
        for k, v in expected.items():
            act = actual.get(k)
            if v != act:
                result.append(f"BAD_{s}({k}:{v}!={act})")

    def _capture_result(self, t: "ytest.YeaTest") -> None:
        test_cfg = t._test_cfg
        if not test_cfg:
            return
        result_list = self._yc.test_check(t)

        failures = []
        state = {}
        for result in result_list:
            if result.failures:
                failures.extend(result.failures)
            if result._state:
                state.update(result._state)

        # print("GOTRES", result)
        result_str = ",".join(failures)
        profile_dict = state.get(":yea:profile")
        # self._results[t._tname] = result_str
        if t._time_end is None or t._time_start is None:
            raise RuntimeError("Test not run")
        elapsed = t._time_end - t._time_start
        tc = junit_xml.TestCase(t.test_id, classname="yea_func", elapsed_sec=elapsed)
        if result_str:
            tc.add_failure_info(message=result_str)
        if profile_dict:
            for metric, stats in profile_dict.items():
                for stat, value in stats.items():
                    tc.add_property(name=f"{metric}::{stat}", value=value)
        self._results.append(tc)

    def run(self, tests: List["ytest.YeaTest"]) -> None:
        self._test_list = tests
        try:
            # inform so we only start monitors needed
            self._yc.monitors_inform(tests)
            self._yc.monitors_init()
            self._yc.monitors_start()
            self._runall()
            self.finish()
        finally:
            self._yc.monitors_stop()

    def _save_results(self) -> None:
        res_fname = self._yc._cfg._results_file
        if not res_fname:
            return
        if self._yc._cfg._cfroot is None:
            raise RuntimeError("No cfroot set")
        p = self._yc._cfg._cfroot.joinpath(res_fname)
        ts = junit_xml.TestSuite("yea-func", self._results)
        # create testfile dir if it doesnt exist
        testdir = p.parent  # get the directory portion of path
        testdir.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            junit_xml.to_xml_report_file(f, [ts], prettyprint=False, encoding="utf-8")

    def finish(self) -> None:
        self.clean()
        self._save_results()
        exit_code = 0
        print("\nResults:")
        print("--------")
        if not self._results:
            sys.exit(exit_code)
        tlen = max(len(tc.name) for tc in self._results)

        use_emoji = not sys.platform.startswith("win")
        for tc in self._results:
            # TODO: fix hack that only looks at first message
            r = tc.failures[0]["message"] if tc.failures else ""
            emoji = "😃" if use_emoji else ":)"
            if r:
                emoji = '🐴 "Neigh" -- ' if use_emoji else 'XX "Neigh" -- '

            print("  {:<{}s}: {}{}".format(tc.name, tlen, emoji, r))
            if r:
                exit_code = 1

        # timing info
        print("\nTest durations (sec):")
        print("---------------------")
        timing_info = sorted(
            ((tc.elapsed_sec, tc.name) for tc in self._results),
            reverse=True,
        )
        for tc in timing_info:
            print(f"  {tc[1]:<{tlen}s}: {tc[0]:.1f}")

        # if we are recalibrating split tests. save them here
        durations_path = self._cfg.durations_path
        store_durations = self._yc._args.store_durations
        if durations_path and store_durations:
            timing_dict = {tc.name: tc.elapsed_sec for tc in self._results}
            with open(durations_path, "w") as f:
                json.dump(timing_dict, f)

        sys.exit(exit_code)

    def get_tests(self) -> List["ytest.YeaTest"]:
        return self._test_list

    def yeadoc_prepare(self, tests: List["ytest.YeaTest"]) -> None:
        """If we have yeadoc tests, copy snippets to actual files."""
        for tst in tests:
            if not tst.is_yeadoc:
                continue
            tpath = tst._tname

            # write test and spec to tempfiles
            shutil.copy(tpath, self._tmpdir)
            t_fname = self._tmpdir / tpath.name
            py_fname = str(t_fname)[:-4] + ".py"

            assert tst._registry
            snippet = tst._registry._yeadoc_dict[tst.yeadoc_id]

            with open(py_fname, "w") as f:
                f.write(snippet.code)

            tst._change_yeadoc_path(pathlib.Path(py_fname))
