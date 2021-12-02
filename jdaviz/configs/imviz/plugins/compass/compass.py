from traitlets import Unicode

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['Compass']


# TODO: This plugin should be per-viewer, not global to Imviz.
@tray_registry('imviz-compass', label="Imviz Compass")
class Compass(TemplateMixin):
    template_file = __file__, "compass.vue"
    data_label = Unicode("").tag(sync=True)
    img_data = Unicode("").tag(sync=True)

    def clear_compass(self):
        """Clear the content of the plugin."""
        self.data_label = ''
        self.img_data = ''

    def draw_compass(self, data_label, img_data):
        """Draw compass in the plugin.
        Input is rendered buffer from Matplotlib.

        """
        self.data_label = data_label
        self.img_data = img_data
