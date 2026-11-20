from traitlets import Bool, Float, observe
from time import sleep

import pytest

from jdaviz import Cubeviz
from jdaviz.app import PrivateApplication
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


@pytest.fixture
def plugin():
    # create an instance of an app with just our fake "Slow" Plugin
    config = get_configuration('cubeviz')
    config['tray'] = ['test-slow-plugin']

    cubeviz_app = PrivateApplication(config)
    cubeviz_helper = Cubeviz(cubeviz_app)

    return cubeviz_helper.plugins['Test Slow Plugin']._obj


def test_is_active(plugin):
    plg = plugin
    plg.open_in_tray(scroll_to=False)
    assert plg.uses_active_status is True
    # Opening the tray without a frontend does not register a visible view.
    assert plg.is_active is False

    assert plg._visible_views == set()
    assert plg.sleep_time == 0
    plg.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    assert plg.is_active is True
    assert plg._visible_views == {'inline'}
    assert plg._method_ran is True

    plg.vue_plugin_visibility({'view_id': 'inline', 'visible': False})
    assert plg.plugin_opened is False
    assert plg.is_active is False

    # if we set sleep_time while the plugin is inactive, the method should not fire
    plg._method_ran = False
    plg.sleep_time = 0.01
    assert plg._method_ran is False
    # but should immediately once it becomes active
    plg.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    assert plg._method_ran is True


def test_multiple_views(plugin):
    changes = []
    plugin.observe(lambda change: changes.append(change['new']), 'is_active')
    for view_id in ('tray', 'inline', 'popout', 'inline'):
        plugin.vue_plugin_visibility({'view_id': view_id, 'visible': True})
    assert changes == [True]
    assert plugin._visible_views == {'tray', 'inline', 'popout'}

    for view_id in ('inline', 'inline', 'unknown', 'tray'):
        plugin.vue_plugin_visibility({'view_id': view_id, 'visible': False})
        assert plugin.plugin_opened is True
        assert plugin.is_active is True
    assert changes == [True]

    plugin.vue_plugin_visibility({'view_id': 'popout', 'visible': False})
    assert plugin._visible_views == set()
    assert plugin.plugin_opened is False
    assert changes == [True, False]


def test_keep_active_and_relevance(plugin):
    plugin.keep_active = True
    assert plugin.is_active is True
    assert plugin.plugin_opened is False
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': False})
    assert plugin.is_active is True

    plugin.irrelevant_msg = 'Not relevant'
    assert plugin.is_active is False
    plugin.vue_plugin_visibility({'view_id': 'popout', 'visible': True})
    assert plugin.plugin_opened is True
    assert plugin.is_active is False
    plugin.keep_active = False
    plugin.irrelevant_msg = ''
    assert plugin.is_active is True
    plugin.vue_plugin_visibility({'view_id': 'popout', 'visible': False})
    assert plugin.is_active is False


def test_as_active(plugin):
    with plugin.as_active():
        assert plugin.is_active is True
        assert plugin.plugin_opened is False
        with plugin.as_active():
            assert plugin.is_active is True
        assert plugin.is_active is True
    assert plugin.is_active is False


def test_no_recompute_without_changes(plugin):
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    assert plugin._method_ran is True
    plugin._method_ran = False
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': False})
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    assert plugin.is_active is True
    assert plugin._method_ran is False


def test_independent_plugin_instances(plugin):
    other = plugin.new()
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    assert other._visible_views == set()
    assert other.is_active is False
    other.vue_plugin_visibility({'view_id': 'inline', 'visible': True})
    plugin.vue_plugin_visibility({'view_id': 'inline', 'visible': False})
    assert plugin.is_active is False
    assert other.is_active is True


def test_popout_close_relay(plugin):
    plugin.vue_plugin_visibility({'view_id': 'tray', 'visible': True})
    plugin.vue_plugin_visibility({'view_id': 'popout', 'visible': True})
    plugin.vue_plugin_visibility({'view_id': 'tray', 'visible': False})
    assert plugin.is_active is True
    assert plugin.visibility_context == {
        'app_id': plugin._app._model_id, 'plugin_id': plugin._model_id}

    plugin._app.vue_plugin_view_closed({
        **plugin.visibility_context, 'view_id': 'popout'})
    assert plugin.is_active is False
    assert plugin._visible_views == set()
    # A duplicate direct/relayed close is harmless.
    plugin._app.vue_plugin_view_closed({
        **plugin.visibility_context, 'view_id': 'popout'})
    assert plugin.is_active is False


def test_popout_close_preserves_other_views(plugin):
    for view_id in ('inline', 'popout', 'another-popout'):
        plugin.vue_plugin_visibility({'view_id': view_id, 'visible': True})
    plugin._app.vue_plugin_view_closed({
        **plugin.visibility_context, 'view_id': 'popout'})
    assert plugin._visible_views == {'inline', 'another-popout'}
    assert plugin.is_active is True


@pytest.mark.parametrize('event', [
    {'view_id': '', 'visible': True},
    {'view_id': None, 'visible': True},
    {'view_id': [], 'visible': True},
    {'view_id': 'inline', 'visible': 'false'},
    {'view_id': 'inline', 'visible': 1},
])
def test_invalid_visibility_event(plugin, event):
    with pytest.raises(ValueError, match='plugin visibility requires'):
        plugin.vue_plugin_visibility(event)
    assert plugin._visible_views == set()
    assert plugin.plugin_opened is False
