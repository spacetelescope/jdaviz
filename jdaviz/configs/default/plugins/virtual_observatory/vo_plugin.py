from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin

__all__ = ["VoPlugin"]
vo_plugin_label = "Virtual Observatory"


@tray_registry("VoPlugin", label=vo_plugin_label)
class VoPlugin(PluginTemplateMixin):
    """Plugin to query the Virtual Observatory and load data into Imviz"""

    template_file = __file__, "vo_plugin.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = (
            "Download data products from VO-registered telescopes and missions."
        )
