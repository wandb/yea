"""Yea test class."""

import configparser
import itertools
import os
import pathlib
import subprocess
import sys
import time

from yea import testcfg, testspec


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

    def _run(self):
        tname = self._tname
        print("INFO: RUN=", tname)
        cmd = "./{}".format(tname)
        tpath = pathlib.Path(tname)
        os.chdir(tpath.parent)
        cmd = "./{}".format(tpath.name)
        # cmd_list = [cmd]
        cmd_list = ["coverage", "run"]
        if self._covrc:
            cmd_list.extend(["--rcfile", str(self._covrc)])
        cmd_list.extend([cmd])
        args = self._test_cfg.get("command-args", [])
        cmd_list.extend(args)
        print("INFO: RUNNING=", cmd_list)
        env = os.environ.copy()
        elist = self._test_cfg.get("env", [])
        for edict in elist:
            env.update(edict)
        if self._permute_groups and self._permute_items:
            env["YEA_PERMUTE_GRP"] = ",".join(self._permute_groups)
            env["YEA_PERMUTE_VAL"] = ",".join(self._permute_items)
        p = subprocess.Popen(cmd_list, env=env)
        try:
            p.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            p.kill()
            try:
                p.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                print("ERROR: double timeout")
                sys.exit(1)
        # print("DONE:", p.returncode)
        self._retcode = p.returncode

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
            self._time_start = time.time()
            self._run()
            self._time_end = time.time()
        self._fin()

    def get_permutations(self):
        self._load()
        perm = self._test_cfg.get("permute")
        if not perm:
            return [self]
        groups = perm.get("group", [])
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
            tid = t._test_cfg.get("id")
            if tid:
                t._test_cfg["id"] = "{}.{}".format(tid, tnum)
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
