"""Registry class."""

import ast
import configparser
import json
import logging
import os
import pathlib
import re
import sys
from typing import Dict, List, Optional, Set, Union

from yea import config, context, split, testspec, ytest
from yea.yeadoc import YeadocSnippet, load_tests_from_docstring

logger = logging.getLogger(__name__)


def convert(text: str) -> Union[int, str]:
    return int(text) if text.isdigit() else text.lower()


def alphanum_sort(key: "ytest.YeaTest") -> List[Union[int, str]]:
    return [convert(c) for c in re.split("([0-9]+)", key._sort_key)]


class Registry:
    _yc: "context.YeaContext"
    _cfg: "config.Config"
    _registry: Set[pathlib.Path]
    # Optional to record that this path has no yearc
    _yearc_dict: Dict[pathlib.Path, Optional[configparser.ConfigParser]]
    _yeadoc_dict: Dict[str, "YeadocSnippet"]
    _yeadoc_set: Set[str]

    def __init__(self, yc: "context.YeaContext") -> None:
        self._yc = yc
        self._cfg = yc._cfg
        self._registry = set()
        self._yearc_dict = {}
        self._yeadoc_dict = {}
        self._yeadoc_set = set()

    def _warn(self, msg: str, path: Optional[pathlib.Path] = None) -> None:
        if path:
            msg = f"{msg} (test: {path})"
        else:
            msg = f"{msg}"
        logger.warn(msg)
        strict = self._yc._args.strict
        err_msg = "ERROR" if strict else "WARNING"
        print(f"{err_msg}: {msg}", file=sys.stderr)
        if strict:
            sys.exit(1)

    def _add_test(self, test_path: pathlib.Path) -> None:
        # TODO: we could add a yearc_list and a spec to the test so it doesnt need
        # to be discovered again
        self._registry.add(test_path)

    def _probe_yearc(self, test_path: pathlib.Path) -> List[configparser.ConfigParser]:
        root = self._yc._cfg._cfroot
        assert root

        # walk until root yearc
        ret = []
        for p in test_path.parents:
            if p == root:
                break

            if p not in self._yearc_dict:
                yearc = p / ".yearc"
                cf = None
                if yearc.exists():
                    cf = configparser.ConfigParser()
                    cf.read(yearc)
                self._yearc_dict[p] = cf

            # if we have a valid config, add to the list for inspection by caller
            cf = self._yearc_dict.get(p)
            if cf:
                ret.append(cf)
        return ret

    def _probe_file_yea(self, test_path: pathlib.Path) -> None:
        # TODO: parse yea file looking for path info
        spec = testspec.load_yaml_from_file(test_path)
        if not spec:
            self._warn("Can not parse file", path=test_path)
            return

        # look for yearc configs which could modify behavior
        yearc_list = self._probe_yearc(test_path)
        is_yeadoc = False
        for cf in yearc_list:
            # for now, just yeadoc specifier
            is_yeadoc = cf.getboolean("yea", "yeadoc", fallback=False)
            if is_yeadoc:
                break

        # if program is specified, keep track of yea file
        py_fname = spec.get("command", {}).get("program")
        if py_fname:
            # hydrate to full path, take base from test_path
            py_fname = test_path.parent.joinpath(*py_fname.split("/"))
        else:
            py_fname = test_path.with_suffix(".py")
            # use this to track the test
            if not is_yeadoc:
                test_path = py_fname

        if is_yeadoc and not self._yc._args.yeadoc:
            logger.warn(f"Skipping yeadoc test because not enabled: {test_path}.")
            return

        if not is_yeadoc:
            if not py_fname.exists():
                self._warn(f"Can not find file: {py_fname}", path=test_path)
                return
        else:
            # yeadoc does not need a py filename, but we should enforce that we have
            # found a snippet from _probe_yeadoc

            # for now, id is required for yeadoc
            test_id: str = spec["id"]

            # add so that _probe_yeadoc_check can validate it was covered
            self._yeadoc_set.add(test_id)
            snippet = self._yeadoc_dict.get(test_id)
            if not snippet:
                self._warn(f"Can not find code referencing: {test_id}", path=test_path)
                return

        self._add_test(test_path)

    def _probe_file_py(self, test_path: pathlib.Path) -> None:
        docstr = testspec.load_docstring(test_path)
        spec = testspec.load_yaml_from_docstring(docstr)
        if spec:
            self._add_test(test_path)

    def _probe_file(self, test_path: pathlib.Path) -> None:
        if test_path.suffix == ".yea":
            self._probe_file_yea(test_path)
        elif test_path.suffix == ".py":
            self._probe_file_py(test_path)
        else:
            self._warn("Ignoring file", path=test_path)

    def _probe_dir(self, path_dir: pathlib.Path) -> None:
        for tpath in path_dir.glob("*.yea"):
            self._probe_file(tpath)
        for tpath in path_dir.glob("*.py"):
            self._probe_file(tpath)

    def _probe_skip_dirs(self, dirs: List) -> None:
        # TODO: temporary hack to avoid walking into wandb dir
        # use .gitignore instead
        if "wandb" in dirs:
            dirs.remove("wandb")
        if ".tox" in dirs:
            dirs.remove(".tox")

    def _probe_walk(self, path_dir: pathlib.Path) -> None:
        self._probe_dir(path_dir)

        for root, dirs, _ in os.walk(path_dir, topdown=True):
            self._probe_skip_dirs(dirs)
            for d in dirs:
                assert self._cfg.test_root
                path_dir = pathlib.Path(self._cfg.test_root, root, d)
                self._probe_dir(path_dir)

    def _probe(self, all_tests: bool, tests: List[str]) -> None:
        if self._cfg.test_root is None:
            raise TypeError("test_root is not set")

        path_dirs: List[pathlib.Path] = []
        if all_tests:
            for tdir in self._cfg.test_dirs:
                path_dir = pathlib.Path(self._cfg.test_root, tdir)
                path_dirs.append(path_dir)
            if tests:
                self._warn("Ignoring test args when using --all")
        else:
            if tests:
                for t in tests:
                    path = pathlib.Path(t)
                    path = path.resolve()
                    if not path.exists():
                        self._warn("Can not find file", path=path)
                    elif path.is_dir():
                        path_dirs.append(path)
                    elif path.is_file():
                        self._probe_file(path)
                    else:
                        self._warn(f"Ignoring test arg {path}")
            else:
                path_dirs.append(pathlib.Path.cwd())

        for path_dir in path_dirs:
            self._probe_walk(path_dir)

    def _probe_yeadoc_dir(self, path_dir: pathlib.Path) -> None:
        # pick up yea tests from docstrings
        id_test_map: Dict[str, YeadocSnippet] = {}

        # build up the list of tests that can be run by parsing docstrings
        for tpath in path_dir.glob("*.py"):

            # parse the test file using ast
            with open(tpath, encoding="utf8") as f:
                mod = ast.parse(f.read())

            doc_strings = []

            function_definitions = [node for node in mod.body if isinstance(node, ast.FunctionDef)]
            for func in function_definitions:
                docstr = ast.get_docstring(func) or ""
                doc_strings.append(docstr)

            classes = [node for node in mod.body if isinstance(node, ast.ClassDef)]
            for class_ in classes:
                methods = [node for node in class_.body if isinstance(node, ast.FunctionDef)]
                for func in methods:
                    docstr = ast.get_docstring(func) or ""
                    doc_strings.append(docstr)
                class_docstr = ast.get_docstring(class_) or ""
                if class_docstr is not None:
                    doc_strings.append(class_docstr)

            for docstr in doc_strings:
                try:
                    snippets = load_tests_from_docstring(docstr)
                except RuntimeError as e:
                    self._warn(f"Unable to parse yeadoc docstr: {e}", path=tpath)
                    continue
                for s in snippets:
                    id_test_map[s.id] = s

        self._yeadoc_dict.update(id_test_map)

    def _probe_yeadoc_walk(self, path_dir: pathlib.Path) -> None:
        self._probe_yeadoc_dir(path_dir)

        for root, dirs, _ in os.walk(path_dir, topdown=True):
            self._probe_skip_dirs(dirs)
            for d in dirs:
                assert self._cfg.test_root
                path_dir = pathlib.Path(self._cfg.test_root, root, d)
                self._probe_yeadoc_dir(path_dir)

    def _probe_yeadoc(self) -> None:
        for yddir in self._cfg.yeadoc_dirs:
            assert self._cfg.test_root
            path_dir = pathlib.Path(self._cfg.test_root, yddir)
            self._probe_yeadoc_walk(path_dir)

    def _probe_yeadoc_check(self) -> None:
        """Validate that all found yeadoc descriptions have tests."""

        for yeadoc_id in self._yeadoc_dict:
            if yeadoc_id not in self._yeadoc_set:
                self._warn(f"Can not find yeadoc test for {yeadoc_id}")

    def probe(self, all_tests: bool = False, tests: Optional[List[str]] = None) -> None:
        tests = tests or []

        if self._registry:
            return

        if self._yc._args.yeadoc:
            self._probe_yeadoc()

        self._probe(all_tests=all_tests, tests=tests)

        if self._yc._args.yeadoc and all_tests:
            self._probe_yeadoc_check()

    def filter_splits(self, tlist: List["ytest.YeaTest"]) -> List["ytest.YeaTest"]:
        splits = self._yc._args.splits
        group = self._yc._args.group
        durations_path = self._cfg.durations_path
        if not splits or not group or not durations_path:
            return tlist

        with open(durations_path) as f:
            durations = json.load(f)

        tlist.sort(key=alphanum_sort)
        groups = split.least_duration(splits=splits, items=tlist, durations=durations)

        my_tests = groups[group - 1].selected
        return my_tests

    def get_tests(self, include_skip: bool = False) -> List["ytest.YeaTest"]:
        tlist: List["ytest.YeaTest"] = []
        for tname in self._registry:
            tname = tname.resolve()
            t = ytest.YeaTest(tname=tname, yc=self._yc)
            if t.skip and not self._yc._args.noskip:
                continue
            test_perms = t.get_permutations()

            # slight hack to add info on a test so it doesnt have to be re-probed
            yearc_list = self._probe_yearc(tname)
            for test in test_perms:
                test._add_yearc_list(yearc_list)
                test._add_registry(self)

            tlist.extend(test_perms)

        tlist = self.filter_splits(tlist)
        tlist.sort(key=alphanum_sort)
        return tlist
