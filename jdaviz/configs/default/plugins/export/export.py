from pathlib import Path
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, SelectPluginComponent,
                                        ViewerSelectMixin, DatasetMultiSelectMixin,
                                        SubsetSelectMixin, MultiselectMixin, with_spinner)
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.user_api import PluginUserApi


__all__ = ['Export']


@tray_registry('export', label="Export")
class Export(PluginTemplateMixin, ViewerSelectMixin, SubsetSelectMixin,
             DatasetMultiSelectMixin, MultiselectMixin):
    """
    See the :ref:`Export Plugin Documentation <export>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """
    template_file = __file__, "export.vue"

    # feature flag for cone support
    dev_dataset_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_subset_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_table_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_plot_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring
    dev_multi_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring

    table_items = List().tag(sync=True)
    table_selected = Any().tag(sync=True)

    plot_items = List().tag(sync=True)
    plot_selected = Any().tag(sync=True)

    viewer_format_items = List().tag(sync=True)
    viewer_format_selected = Unicode().tag(sync=True)

    filename = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.table = SelectPluginComponent(self,
                                           items='table_items',
                                           selected='table_selected',
                                           multiselect='multiselect',
                                           default_mode='empty',
                                           manual_options=['table-tst1', 'table-tst2'])

        self.plot = SelectPluginComponent(self,
                                          items='plot_items',
                                          selected='plot_selected',
                                          multiselect='multiselect',
                                          default_mode='empty',
                                          manual_options=['plot-tst1', 'plot-tst2'])

        viewer_format_options = ['png', 'svg']
        if self.app.config == 'cubeviz' and not self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the movie in python would save on the server, not
            # on the user's machine, so movie support in cubeviz should be disabled
            viewer_format_options += ['mp4']

        self.viewer_format = SelectPluginComponent(self,
                                                   items='viewer_format_items',
                                                   selected='viewer_format_selected',
                                                   manual_options=viewer_format_options)

        # default selection:
        self.dataset._default_mode = 'empty'
        self.viewer.select_default()
        self.filename = f"{self.app.config}_export"

    @property
    def user_api(self):
        # TODO: backwards compat for save_movie, etc
        # TODO: expose export once API is finalized
        expose = ['viewer', 'viewer_format']

        if self.dev_dataset_support:
            expose += ['dataset']
        if self.dev_subset_support:
            expose += ['subset']
        if self.dev_table_support:
            expose += ['table']
        if self.dev_plot_support:
            expose += ['plot']
        if self.dev_multi_support:
            expose += ['multiselect']

        return PluginUserApi(self, expose=expose)

    @observe('multiselect', 'viewer_multiselect')
    def _sync_multiselect_traitlets(self, event):
        # ViewerSelectMixin brings viewer_multiselect, but we want a single traitlet to control
        # all select inputs, so we'll keep them synced here and only expose multiselect through
        # the user API
        self.multiselect = event.get('new')
        self.viewer_multiselect = event.get('new')
        if not self.multiselect:
            # default to just a single viewer
            self._sync_singleselect({'name': 'viewer', 'new': self.viewer_selected})

    @observe('viewer_selected', 'dataset_selected', 'subset_selected',
             'table_selected', 'plot_selected')
    def _sync_singleselect(self, event):
        if not hasattr(self, 'dataset') or not hasattr(self, 'viewer'):
            # plugin not fully intialized
            return
        # if multiselect is not enabled, only allow a single selection across all select components
        if self.multiselect:
            return
        if event.get('new') in ('', []):
            return
        name = event.get('name')
        for attr in ('viewer_selected', 'dataset_selected', 'subset_selected',
                     'table_selected', 'plot_selected'):
            if name != attr:
                setattr(self, attr, '')

    @with_spinner()
    def export(self, filename=None, show_dialog=None):
        """
        """
        if self.dataset.selected is not None and len(self.dataset.selected):
            raise NotImplementedError("dataset export not yet supported")
        if self.subset.selected is not None and len(self.subset.selected):
            raise NotImplementedError("subset export not yet supported")
        if self.table.selected is not None and len(self.table.selected):
            raise NotImplementedError("table export not yet supported")
        if self.plot.selected is not None and len(self.plot.selected):
            raise NotImplementedError("plot export not yet supported")
        if self.multiselect:
            raise NotImplementedError("batch export not yet supported")

        if not len(self.viewer.selected):
            raise ValueError("no viewers selected to export")

        viewer = self.viewer.selected_obj
        filename = filename if filename is not None else self.filename
        filetype = self.viewer_format.selected

        # at this point, we can assume only a single figure is selected
        if len(filename):
            if not filename.endswith(filetype):
                filename += f".{filetype}"
            filename = Path(filename).expanduser()
        else:
            filename = None

        if filetype == "png":
            if filename is None or show_dialog:
                viewer.figure.save_png(str(filename) if filename is not None else None)
            else:
                if not filename.parent.exists():
                    raise ValueError(f"Invalid path={filename.parent}")

                # support writing without save dialog
                # https://github.com/bqplot/bqplot/pull/1397
                def on_img_received(data):
                    try:
                        with filename.open(mode='bw') as f:
                            f.write(data)
                    except Exception as e:
                        self.hub.broadcast(SnackbarMessage(
                            f"{self.viewer.selected} failed to export to {str(filename)}: {e}",
                            sender=self, color="error"))
                    finally:
                        self.hub.broadcast(SnackbarMessage(
                            f"{self.viewer.selected} exported to {str(filename)}",
                            sender=self, color="success"))

                if viewer.figure._upload_png_callback is not None:
                    raise ValueError("previous png export is still in progress.  Wait to complete "
                                     "before making another call to save_figure")

                viewer.figure.get_png_data(on_img_received)

        elif filetype == "svg":
            viewer.figure.save_svg(str(filename) if filename is not None else None)

        else:  # pragma: no cover
            raise NotImplementedError(f"filetype={filetype} not supported")

    def vue_export_from_ui(self, *args, **kwargs):
        try:
            self.export(show_dialog=True)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Export failed with: {e}", sender=self, color="error"))
            raise# for debugging only
