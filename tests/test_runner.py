import pathlib
from unittest import mock

import pytest

from yea.context import YeaContext
from yea.registry import Registry
from yea.runner import TestRunner as Runner  # not to confuse pytest


@pytest.mark.parametrize(
    "mocked_yea_context",
    [
        {
            "action": "run",
            "tests": [
                "tests/assets/sample01.yea",
                "tests/assets/sample02.yea",
            ],
        }
    ],
    indirect=True,
)
def test_runner_skip(mocked_yea_context: YeaContext):
    yc = mocked_yea_context
    registry = Registry(yc=yc)
    registry.probe(tests=yc._args.tests)
    tests_to_run = {t._tname for t in registry.get_tests()}
    assert pathlib.Path("tests/assets/sample01.yea").resolve() not in tests_to_run
    assert pathlib.Path("tests/assets/sample02.yea").resolve() in tests_to_run


@pytest.mark.parametrize(
    "mocked_yea_context",
    [
        {
            "action": "run",
            "tests": [
                "tests/assets/sample03.py",
            ],
        }
    ],
    indirect=True,
)
def test_runner_skips_platform(mocked_yea_context: YeaContext):
    with mock.patch("sys.platform", "windows 95"):
        yc = mocked_yea_context
        registry = Registry(yc=yc)
        registry.probe(tests=yc._args.tests)
        tests_to_run = {t._tname for t in registry.get_tests()}
        assert len(tests_to_run) == 0
    with mock.patch("sys.platform", "darwin"):
        yc = mocked_yea_context
        registry = Registry(yc=yc)
        registry.probe(tests=yc._args.tests)
        tests_to_run = {t._tname for t in registry.get_tests()}
        assert len(tests_to_run) == 1
        assert pathlib.Path("tests/assets/sample03.py").resolve() in tests_to_run


@pytest.mark.parametrize(
    "mocked_yea_context",
    [
        {
            "action": "run",
            "tests": [
                "tests/assets/sample03.py",
            ],
        }
    ],
    indirect=True,
)
def test_runner_run(mocked_yea_context: YeaContext, capsys):
    with mock.patch("sys.platform", "darwin"):
        yc = mocked_yea_context
        registry = Registry(yc=yc)
        registry.probe(tests=yc._args.tests)
        runner = Runner(yc=mocked_yea_context)
        tests = registry.get_tests()
        runner.run(tests=tests)
        captured = capsys.readouterr().out
        assert "assets.sample03" in captured
        assert "INFO: RUNNING= ['coverage', 'run', '--rcfile'," in captured
        assert "Results:" in captured
        assert "😃" in captured
        assert "Test durations (sec):" in captured
        assert "SystemExit: 0" in captured
