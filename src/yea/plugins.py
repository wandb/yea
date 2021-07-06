"""Plugins."""

import sys
if sys.version_info < (3, 10):
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points




class Plugins:
    def __init__(self, yc):
        self._yc = yc
        self._plugin_list = []
        self._find_plugins()

    def _find_plugins(self):
        discovered_plugins = entry_points(group='yea.plugins')
        for p in discovered_plugins:
            # print("got", p)
            m = p.load()
            # print("got", m)
            plug = m.init_plugin(self._yc)
            self._plugin_list.append(plug)

    def monitors_init(self):
        for p in self._plugin_list:
            p.monitors_init()

    def monitors_start(self):
        for p in self._plugin_list:
            p.monitors_start()

    def monitors_stop(self):
        for p in self._plugin_list:
            p.monitors_stop()

    def monitors_reset(self):
        for p in self._plugin_list:
            p.monitors_reset()

    def test_prep(self, yt):
        # wandb_dir_safe_cleanup()
        for p in self._plugin_list:
            p.test_prep(yt)

    def test_done(self, yt):
        # wandb_dir_safe_cleanup()
        for p in self._plugin_list:
            p.test_done(yt)

    def test_check(self, yt):
        # ctx = self._backend.get_state()
        result_list = []
        for p in self._plugin_list:
            result = p.test_check(yt)
            if result:
                result_list.extend(result)
        return result_list
