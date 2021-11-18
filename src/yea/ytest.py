"""Yea test class."""

import configparser
import itertools
import json
import os
import pathlib
import subprocess
import sys
import time

import requests

from yea import testcfg, testspec


def run_command(cmd_list, timeout=None, env=None):
    env = env or os.environ
    timeout = timeout or 300
    print("INFO: RUNNING=", cmd_list)
    p = subprocess.Popen(cmd_list, env=env)
    try:
        p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        print("ERROR: TIMEOUT")
        p.kill()
        try:
            p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            print("ERROR: double timeout")
            sys.exit(1)
    print("INFO: exit=", p.returncode)
    return p.returncode


def download(url, fname):
    err = False
    print(f"INFO: grabbing {fname} from {url}")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(fname, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.HTTPError as e:
        print("ERROR: url download error", url, e)
        err = True
    return err


class YeaTest:
    def __init__(self, *, tname, yc):
        self._tname = tname
        self._yc = yc
        self._args = yc._args
        self._retcode = None
        self._test_cfg = None
        self._covrc = None
        self._time_start = None
        self._time_end = None
        self._permute_groups = None
        self._permute_items = None

    def __str__(self):
        return "{}".format(self._tname)

    def _depend_files(self):
        err = False
        dep = self._test_cfg.get("depend", {})
        files = dep.get("files", [])
        for fdict in files:
            fn = fdict["file"]
            fs = fdict["source"]
            assert fs.startswith("http"), "only http schemes supported right now"
            err = err or download(fs, fn)
        return err

    def _depend_install(self):
        err = False
        req = self._test_cfg.get("depend", {}).get("requirements", [])
        options = self._test_cfg.get("depend", {}).get("pip_install_options", [])
        timeout = self._test_cfg.get("depend", {}).get("pip_install_timeout")
        if not (req or options):
            return err
        if req:
            fname = ".yea-requirements.txt"
            with open(fname, "w") as f:
                f.writelines(f"{item}\n" for item in req)
            options += ["-r", fname]
        cmd_list = ["pip", "install", "-qq"]
        cmd_list.extend(options)
        exit_code = run_command(cmd_list, timeout=timeout)
        if req and os.path.exists(fname):
            os.remove(fname)
        err = err or exit_code != 0
        return err

    def _depend_uninstall(self):
        err = False
        req = self._test_cfg.get("depend", {}).get("uninstall", [])
        timeout = self._test_cfg.get("depend", {}).get("pip_uninstall_timeout")
        if not req:
            return err
        fname = ".yea-uninstall.txt"
        with open(fname, "w") as f:
            f.writelines(f"{item}\n" for item in req)
        cmd_list = ["pip", "uninstall", "-qq", "-y", "-r", fname]
        exit_code = run_command(cmd_list, timeout=timeout)
        if os.path.exists(fname):
            os.remove(fname)
        err = err or exit_code != 0
        return err

    def _depend(self):
        tname = self._tname
        print("INFO: DEPEND=", tname)
        tpath = pathlib.Path(tname)
        os.chdir(tpath.parent)
        err = False
        err = err or self._depend_uninstall()
        err = err or self._depend_files()
        err = err or self._depend_install()

        return err

    def _run(self):
        tname = self._tname
        print("INFO: RUN=", tname)
        program = self._test_cfg.get("command", {}).get("program")
        tpath = pathlib.Path(tname)
        os.chdir(tpath.parent)
        cmd = "./{}".format(program or tpath.name)
        # cmd_list = [cmd]
        cmd_list = ["coverage", "run"]
        if self._covrc:
            cmd_list.extend(["--rcfile", str(self._covrc)])
        cmd_list.extend([cmd])
        cmd_cfg = self._test_cfg.get("command", {})
        args = cmd_cfg.get("args", [])
        timeout = cmd_cfg.get("timeout")
        cmd_list.extend(args)
        env = os.environ.copy()
        elist = self._test_cfg.get("env", [])
        for edict in elist:
            env.update(edict)
        if self._permute_groups and self._permute_items:
            env["YEA_PARAM_NAMES"] = ",".join(self._permute_groups)
            env["YEA_PARAM_VALUES"] = ",".join(self._permute_items)

        plugins = self._test_cfg.get("plugin", [])
        if plugins:
            for p in plugins:
                penv = p.upper()
                pnames = []
                pvalues = []
                for items in self._test_cfg.get("var", []):
                    for k, v in items.items():
                        prefix = f":{p}:"
                        if k.startswith(prefix):
                            pnames.append(k[len(prefix) :])
                            pvalues.append(v)
                if pnames and pvalues:
                    env[f"YEA_PLUGIN_{penv}_NAMES"] = ",".join(pnames)
                    env[f"YEA_PLUGIN_{penv}_VALUES"] = json.dumps(pvalues)
            env["YEA_PLUGINS"] = ",".join(plugins)

        exit_code = run_command(cmd_list, env=env, timeout=timeout)
        self._retcode = exit_code

    def _load(self):
        spec = None
        # load yea file if exists
        fname = str(self._tname)
        if fname.endswith(".py"):
            yea_name = fname[:-3] + ".yea"
            if os.path.exists(yea_name):
                spec = testspec.load_yaml_from_file(yea_name)
        elif fname.endswith(".yea"):
            spec = testspec.load_yaml_from_file(fname)
        if not spec:
            docstr = testspec.load_docstring(self._tname)
            spec = testspec.load_yaml_from_docstring(docstr)
        # print("SPEC:", self._tname, spec)
        cfg = testcfg.TestlibConfig(spec)
        # print("TESTCFG", cfg)
        self._test_cfg = cfg

    def _prep(self):
        """Cleanup and/or populate wandb dir."""
        self._yc.test_prep(self)
        # load file and docstring eval criteria
        self._setup_coverage_file()
        self._setup_coverage_config()

    def _setup_coverage_file(self):
        # dont mess with coverage_file (for now) if already set
        if self._yc._covfile:
            return
        covfname = ".coverage-{}-{}".format(self._yc._pid, self.test_id)
        covfile = self._yc._cachedir.joinpath(covfname)
        os.environ["COVERAGE_FILE"] = str(covfile)

    def _setup_coverage_config(self):
        # do we have a template?
        template = self._yc._cfg._coverage_config_template
        if not template:
            return
        cov_src = self._yc._cfg._coverage_source
        cov_env = self._yc._cfg._coverage_source_env
        if cov_env:
            cov_env_src = os.environ.get(cov_env)
            if cov_env_src:
                cov_src = cov_env_src
        if not cov_src:
            return

        # find our sources
        #   sourceis from tox (set in env)
        #   or set from conf (if not in env)
        p = self._yc._cfg._cfroot.joinpath(template)
        assert p.exists()
        cf = configparser.ConfigParser()
        cf.read(p)

        cf["run"]["source"] = cov_src

        covrc_fname = "yea-covrc-{}-{}.conf".format(self._yc._pid, self.test_id)
        covrc = self._yc._cachedir.joinpath(covrc_fname)
        with open(covrc, "w") as configfile:
            cf.write(configfile)

        self._covrc = covrc

    def _fin(self):
        """Reap anything in wandb dir"""
        self._yc.test_done(self)

    def run(self):
        self._prep()
        if not self._args.dryrun:
            err = self._depend()
            # TODO: record error insted of assert
            assert not err, "Problem getting test dependencies"
            self._time_start = time.time()
            self._run()
            self._time_end = time.time()
        self._fin()

    def get_permutations(self):
        self._load()
        params = self._test_cfg.get("parametrize")
        if not params:
            return [self]
        groups = params.get("permute", [])
        gnames = []
        glist = []
        for g in groups:
            assert isinstance(g, dict)
            assert len(g) == 1
            k = next(iter(g))
            gnames.append(k)
            v = g[k]
            assert isinstance(v, list)
            glist.append(v)
        items = list(itertools.product(*glist))
        r = []
        for tnum, it in enumerate(items):
            t = YeaTest(tname=self._tname, yc=self._yc)
            t._load()
            t._permute_groups = gnames
            t._permute_items = it
            tpname = "{}-{}".format(tnum, "-".join(it))
            tid = t._test_cfg.get("id")
            if tid:
                t._test_cfg["id"] = "{}.{}".format(tid, tpname)
            r.append(t)
        return r

    @property
    def name(self):
        root = self._yc._cfg._cfroot
        b = self._tname.relative_to(root)
        return str(b)

    @property
    def test_id(self):
        tid = self._test_cfg.get("id") if self._test_cfg else None
        return tid

    @property
    def _sort_key(self):
        tid = self._test_cfg.get("id") if self._test_cfg else ""
        return tid + ":" + self.name

    @property
    def config(self):
        return self._test_cfg
