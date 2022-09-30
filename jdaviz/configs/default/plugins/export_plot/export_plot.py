from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi

__all__ = ['ExportViewer']


@tray_registry('g-export-plot', label="Export Plot")
class ExportViewer(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Export Plot Plugin Documentation <imviz-export-plot>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`save_figure`
    """
    template_file = __file__, "export_plot.vue"

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('save_figure',))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save_figure(self, filename=None, filetype=None):
        """
        Save the figure to an image with a provided filename or through an interactive save dialog.

        Parameters
        ----------
        filename : str or `None`
            Filename to autopopulate the save dialog.
        filetype : {'png', 'svg', `None`}
            Filetype (PNG or SVG).  If `None`, will default based on filename or to PNG.

        """
        if filetype is None:
            if filename is not None and '.' in filename:
                filetype = filename.split('.')[-1]
            else:
                # default to png
                filetype = 'png'

        viewer = self.viewer.selected_obj
        if filetype == "png":
            viewer.figure.save_png(filename)
        elif filetype == "svg":
            viewer.figure.save_svg(filename)
        else:
            raise NotImplementedError(f"filetype={filetype} not supported")

    def vue_save_figure(self, filetype):
        """
        Callback for save figure events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        self.save_figure(filetype=filetype)
