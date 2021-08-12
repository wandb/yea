import multiprocessing as mp
import os


def setup_mp():
    names = os.environ.get("YEA_PARAM_NAMES")
    values = os.environ.get("YEA_PARAM_VALUES")
    if not names or not values:
        return
    names = names.split(",")
    values = values.split(",")
    params = dict(zip(names, values))
    start_method = params.get(":yea:start_method")
    if not start_method:
        return
    print(f"INFO: start_method= {start_method}")
    mp.set_start_method(start_method)
    # TODO: check mp setup?


def setup():
    setup_mp()
