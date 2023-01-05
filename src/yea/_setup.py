import importlib
import json
import multiprocessing as mp
import os
from typing import Dict, List, Optional, Tuple


def _setup_params() -> Dict[str, str]:
    env_names = os.environ.get("YEA_PARAM_NAMES")
    env_values = os.environ.get("YEA_PARAM_VALUES")
    if env_names is None or env_values is None:
        return dict()
    names = env_names.split(",")
    values = env_values.split(",")
    params = dict(zip(names, values))
    return params


def _setup_profile() -> Optional[Tuple[str, Dict[str, str]]]:
    prof_file = os.environ.get("YEA_PROFILE_FILE")
    prof_vars = os.environ.get("YEA_PROFILE_VARS")
    prof_vals = os.environ.get("YEA_PROFILE_VALS")
    if any(v is None for v in (prof_file, prof_vals, prof_vars)):
        return None
    # make linter happy
    assert prof_file and prof_vars and prof_vals

    p_vars = prof_vars.split(",")
    p_vals = json.loads(prof_vals)
    params = dict(zip(p_vars, p_vals))
    return (prof_file, params)


def _setup_trigger() -> Optional[List[str]]:
    trig_vars = os.environ.get("YEA_TRIGGER_VARS")
    if not trig_vars:
        return None
    t_vars = trig_vars.split(",")
    return t_vars


def setup_mp(params: Dict[str, str]) -> None:
    start_method = params.get(":yea:start_method")
    if not start_method:
        return
    print(f"INFO: start_method= {start_method}")
    mp.set_start_method(start_method)
    # TODO: check mp setup?


def setup_plugins() -> None:
    env_plugins = os.environ.get("YEA_PLUGINS")
    if env_plugins is None:
        return
    plugins = env_plugins.split(",")
    for plug in plugins:
        mod_name = f"yea_{plug}"
        mod = importlib.import_module(mod_name)
        mod_setup = getattr(mod, "setup", None)
        if not mod_setup:
            continue
        mod_setup()


def setup() -> None:
    p = _setup_params()
    setup_mp(params=p)
    setup_plugins()
