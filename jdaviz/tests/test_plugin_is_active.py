from traitlets import Bool, Float, observe
from time import sleep

from jdaviz import Cubeviz
from jdaviz.app import Application
from jdaviz.core.config import get_configuration
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, skip_if_no_updates_since_last_active


@tray_registry('test-slow-plugin', label="Test Slow Plugin")
class SlowPlugin(PluginTemplateMixin):
    """
    empty plugin with a simulated slow method
    """
    template = ''
    uses_active_status = Bool(True).tag(sync=True)
    sleep_time = Float(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        # reset this manually in the test to see if slow_method ran since last manual reset
        self._method_ran = False
        super().__init__(*args, **kwargs)

    @observe('is_active', 'sleep_time')
    @skip_if_no_updates_since_last_active()
    def slow_method(self, *args):
        self._method_ran = True
        sleep(self.sleep_time)
        return


def test_is_active():
    # create an instance of an app with just our fake "Slow" Plugin
    config = get_configuration('cubeviz')
    config['tray'] = ['test-slow-plugin']

    cubeviz_app = Application(config)
    cubeviz_helper = Cubeviz(cubeviz_app)

    plg = cubeviz_helper.plugins['Test Slow Plugin']._obj
    plg.open_in_tray()
    assert plg.uses_active_status is True
    # there is no actual frontend here to ping (this would be True in a notebook)
    assert plg.is_active is False

    # so we need to fake the pings
    assert plg._ping_timestamp == 0
    assert plg.sleep_time == 0
    plg.vue_plugin_ping({})
    # since the observe on is_active/sleep_time returns immediately, the plugin is active
    assert plg.is_active is True
    assert plg._ping_timestamp > 0
    assert plg._method_ran is True

    # if there are no pings then the plugin will reset to inactive
    sleep(1)
    assert plg.is_active is False

    # if we set sleep_time while the plugin is inactive, the method should not fire
    plg._method_ran = False
    plg.sleep_time = 0.01
    assert plg._method_ran is False
    # but should immediately once it becomes active
    plg.vue_plugin_ping({})
    assert plg._method_ran is True
