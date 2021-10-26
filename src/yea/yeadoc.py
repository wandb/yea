import ast
import io
import re
import logging
from dataclasses import dataclass
import pathlib
from typing import Dict, List, Optional
from yea.runner import TestRunner, alphanum_sort
from yea import testspec, ytest
import tempfile
import shutil

logger = logging.getLogger(__name__)


@dataclass
class YeadocSnippet:
    code: str
    lineno: int
    id: str
    syntax: Optional[str] = None


def extract_from_buffer(f, max_num_lines: int = 10000) -> List[YeadocSnippet]:
    out = []
    previous_nonempty_line = None
    k = 1

    while True:
        line = f.readline()
        k += 1
        if not line:
            # EOF
            break

        if line.strip() == "":
            continue

        if line.lstrip()[:3] == "```":
            syntax = line.strip()[3:]
            num_leading_spaces = len(line) - len(line.lstrip())
            lineno = k - 1
            # read the block
            code_block = []
            while True:
                line = f.readline()
                k += 1
                if not line:
                    raise RuntimeError("Hit end-of-file prematurely. Syntax error?")
                if k > max_num_lines:
                    raise RuntimeError(f"File too large (> {max_num_lines} lines). Set max_num_lines.")
                # check if end of block
                if line.lstrip()[:3] == "```":
                    break
                # Cut (at most) num_leading_spaces leading spaces
                nls = min(num_leading_spaces, len(line) - len(line.lstrip()))
                line = line[nls:]
                code_block.append(line)

            if previous_nonempty_line is None:
                previous_nonempty_line = line
                continue

            # check for keywords
            m = re.match(
                r"<!--[-\s]*yeadoc-test:(.*)-->",
                previous_nonempty_line.strip(),
            )
            if m is None:
                pass  # ignore test because it is not labeled
            else:
                id = m.group(1).strip("- ")
                out.append(YeadocSnippet("".join(code_block), lineno, id, syntax))
                continue

        previous_nonempty_line = line

    return out


def load_tests_from_docstring(docstring: str) -> List[YeadocSnippet]:
    return extract_from_buffer(io.StringIO(docstring))


class DocTestRunner(TestRunner):
    def __init__(self, *, yc):
        self._tmpdir = pathlib.Path.cwd() / ".yeadoc"
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir)
        self._tmpdir.mkdir()
        super().__init__(yc=yc)

    def _populate(self):
        tpaths = []

        args_tests = self._get_args_list() or []

        all_tests = False
        if self._args.action == "list" and not self._args.tests:
            all_tests = True
        if self._args.action == "run" and self._args.all:
            all_tests = True

        id_test_map: Dict[str, YeadocSnippet] = {}

        for path_dir in self._get_dirs():
            # build up the list of tests that can be run by parsing docstrings
            for tpath in path_dir.glob("*.py"):

                # parse the test file using ast
                with open(tpath) as f:
                    mod = ast.parse(f.read())

                function_definitions = [node for node in mod.body if isinstance(node, ast.FunctionDef)]
                for func in function_definitions:
                    docstr = ast.get_docstring(func)
                    snippets = load_tests_from_docstring(docstr)
                    for s in snippets:
                        id_test_map[s.id] = s

        for path_dir in self._get_dirs():
            for tpath in path_dir.glob("*.yea"):
                # TODO: parse yea file looking for path info
                spec = testspec.load_yaml_from_file(tpath)
                id_not_in_map = spec.get("id", None) not in id_test_map
                test_selected_to_run = all_tests or spec.get("id", None) in args_tests

                if id_not_in_map or not test_selected_to_run:
                    logger.debug("skip yea fname: {}".format(tpath))
                    continue

                if all_tests:
                    if spec.get("tag", {}).get("skip", False):
                        continue
                    suite = spec.get("tag", {}).get("suite", "main")
                    shard = spec.get("tag", {}).get("shard", "default")
                    if self._args.suite and self._args.suite != suite:
                        continue
                    if self._args.shard and self._args.shard != shard:
                        continue

                # write test and spec to tempfiles
                shutil.copy(tpath, self._tmpdir)
                t_fname = self._tmpdir / tpath.name
                py_fname = str(t_fname)[:-4] + ".py"
                with open(py_fname, "w") as f:
                    f.write(id_test_map[spec["id"]].code)

                # add .yea or .py file
                tpaths.append(pathlib.Path(t_fname))

        tlist = []
        for tname in tpaths:
            t = ytest.YeaTest(tname=tname, yc=self._yc)
            test_perms = t.get_permutations()
            tlist.extend(test_perms)

        tlist.sort(key=alphanum_sort)
        self._test_list = tlist

    def clean(self):
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir)

    def finish(self):
        self.clean()
        super().finish()
