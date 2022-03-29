from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, ViewerSelectMixin

__all__ = ['ExportViewer']


@tray_registry('g-export-plot', label="Export Plot")
class ExportViewer(TemplateMixin, ViewerSelectMixin):
    template_file = __file__, "export_plot.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def vue_save_figure(self, filetype):
        """
        Callback for save figure events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        viewer = self.viewer.selected_obj
        if filetype == "png":
            viewer.figure.save_png()
        elif filetype == "svg":
            viewer.figure.save_svg()
