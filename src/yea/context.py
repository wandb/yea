"""yea context."""

from yea import config
from yea import plugins


class YeaContext:
    def __init__(self, *, args):
        self._args = args
        self._cfg = config.Config()
        self._plugs = plugins.Plugins(yc=self)

    def is_live(self):
        return self._args.live

    def monitors_init(self):
        self._plugs.monitors_init()

    def monitors_start(self):
        self._plugs.monitors_start()

    def monitors_stop(self):
        self._plugs.monitors_stop()

    def monitors_reset(self):
        self._plugs.monitors_reset()

    def test_prep(self, yt):
        # wandb_dir_safe_cleanup()
        self._plugs.test_prep(yt)

    def test_done(self, yt):
        # wandb_dir_safe_cleanup()
        self._plugs.test_done(yt)

    def test_check(self, yt):
        # ctx = self._backend.get_state()
        result_list = self._plugs.test_check(yt)
        return result_list
