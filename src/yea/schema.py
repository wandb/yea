# lifted from github.com/wandb/sweeps

import json
from pathlib import Path

import jsonschema  # type:ignore
from jsonschema import Draft7Validator

testlib_config_jsonschema_fname = Path(__file__).parent / "schema-wandb-testlib.json"
with open(testlib_config_jsonschema_fname, "r") as f:
    testlib_config_jsonschema = json.load(f)


format_checker = jsonschema.FormatChecker()


@format_checker.checks("float")
def float_checker(value):
    return isinstance(value, float)


@format_checker.checks("integer")
def int_checker(value):
    return isinstance(value, int)


validator = Draft7Validator(
    schema=testlib_config_jsonschema, format_checker=format_checker
)
