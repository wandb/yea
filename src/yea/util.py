import os
import sys
from importlib import import_module
from typing import Any, Callable


def vendor_setup() -> Callable:
    """This enables us to use the vendor directory for packages we don't depend on
    Returns a function to call after imports are complete. Make sure to call this
    function or you will modify the user's path which is never good. The pattern should be:
    reset_path = vendor_setup()
    # do any vendor imports...
    reset_path()
    """
    original_path = [directory for directory in sys.path]

    def reset_import_path() -> None:
        sys.path = original_path

    parent_dir = os.path.abspath(os.path.dirname(__file__))
    vendor_dir = os.path.join(parent_dir, "vendor")
    vendor_packages = ("junit_xml",)
    package_dirs = [os.path.join(vendor_dir, p) for p in vendor_packages]
    for p in [vendor_dir] + package_dirs:
        if p not in sys.path:
            sys.path.insert(1, p)

    return reset_import_path


def vendor_import(name: str) -> Any:
    reset_path = vendor_setup()
    module = import_module(name)
    reset_path()
    return module
