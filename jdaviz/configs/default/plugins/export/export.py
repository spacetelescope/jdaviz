import os
import time
from pathlib import Path
import threading

from astropy import units as u
from astropy.nddata import CCDData
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue_jupyter.bqplot.image import BqplotImageView
from regions import CircleSkyRegion, EllipseSkyRegion
from specutils import Spectrum
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty, IntHandleEmpty
from jdaviz.core.marks import ShadowMixin
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, SelectPluginComponent,
                                        ViewerSelectMixin, DatasetMultiSelectMixin,
                                        SubsetSelectMixin, PluginTableSelectMixin,
                                        PluginPlotSelectMixin, AutoTextField,
                                        MultiselectMixin, with_spinner)
from jdaviz.core.events import AddDataMessage, SnackbarMessage
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.region_translators import region2stcs_string

try:
    import cv2
except ImportError:
    HAS_OPENCV = False
else:
    HAS_OPENCV = True

__all__ = ['Export']


@tray_registry('export', label="Export",
               category='core', sidebar='save')
class Export(PluginTemplateMixin, ViewerSelectMixin, SubsetSelectMixin,
             DatasetMultiSelectMixin, PluginTableSelectMixin, PluginPlotSelectMixin,
             MultiselectMixin):
    """
    See the :ref:`Export Plugin Documentation <imviz-export-plot>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`)
    * ``viewer_format`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``image_custom_size`` (Bool)
    * ``image_width`` (int)
        The width of the image to export, in pixels, if ``image_custom_size`` is `True`.
    * ``image_height`` (int)
        The height of the image to export, in pixels, if ``image_custom_size`` is `True`.
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`)
    * ``dataset_format`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`)
    * ``subset_format`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``plugin_table`` (:class:`~jdaviz.core.template_mixin.PluginTableSelect`)
    * ``plugin_table_format`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``plugin_plot`` (:class:`~jdaviz.core.template_mixin.PluginPlotSelect`)
    * ``plugin_plot_format`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`)
    * ``filename``
    * :meth:`export`
    """
    template_file = __file__, "export.vue"

    dev_multi_support = Bool(False).tag(sync=True)  # when enabling: add entries to docstring

    viewer_format_items = List().tag(sync=True)
    viewer_format_selected = Unicode().tag(sync=True)
    image_custom_size = Bool(False).tag(sync=True)
    image_width = IntHandleEmpty(800).tag(sync=True)
    image_height = IntHandleEmpty(600).tag(sync=True)

    plugin_table_format_items = List().tag(sync=True)
    plugin_table_format_selected = Unicode().tag(sync=True)

    subset_format_items = List().tag(sync=True)
    subset_format_selected = Unicode().tag(sync=True)

    dataset_format_items = List().tag(sync=True)
    dataset_format_selected = Unicode().tag(sync=True)

    # copy of widget of the selected plugin_plot in case the parent plugin is not opened
    plugin_plot_selected_widget = Unicode().tag(sync=True)

    plugin_plot_format_items = List().tag(sync=True)
    plugin_plot_format_selected = Unicode().tag(sync=True)

    filename_value = Unicode().tag(sync=True)
    filename_default = Unicode().tag(sync=True)
    filename_auto = Bool(True).tag(sync=True)
    filename_invalid_msg = Unicode('').tag(sync=True)

    default_filepath = Unicode().tag(sync=True)

    # if selected subset is spectral or composite, display message and disable export
    subset_invalid_msg = Unicode().tag(sync=True)
    data_invalid_msg = Unicode().tag(sync=True)
    subset_format_invalid_msg = Unicode().tag(sync=True)

    # We currently disable exporting spectrum-viewer in Cubeviz
    viewer_invalid_msg = Unicode().tag(sync=True)

    # For Cubeviz movie.
    movie_enabled = Bool(False).tag(sync=True)
    i_start = IntHandleEmpty(0).tag(sync=True)
    i_end = IntHandleEmpty(0).tag(sync=True)
    movie_fps = FloatHandleEmpty(5.0).tag(sync=True)
    movie_recording = Bool(False).tag(sync=True)
    movie_interrupt = Bool(False).tag(sync=True)

    overwrite_warn = Bool(False).tag(sync=True)

    # This is a temporary measure to allow server-installations to disable saving server-side until
    # saving client-side is supported for all exports.
    serverside_enabled = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.filename = AutoTextField(self, 'filename_value',
                                      'filename_default',
                                      'filename_auto',
                                      'filename_invalid_msg')

        # description displayed under plugin title in tray
        self._plugin_description = 'Export data/plots and other outputs to a file.'

        # NOTE: if adding export support for non-plugin products, also update the language
        # in the UI as well as in _set_dataset_not_supported_msg
        self.dataset.filters = ['is_not_wcs_only', 'not_child_layer',
                                'from_plugin']

        self.viewer.add_filter('is_not_empty')

        viewer_format_options = ['png', 'svg']
        if self.config == 'cubeviz':
            if not self.app.state.settings.get('server_is_remote'):
                viewer_format_options += ['mp4']
                # still list mp4 as an option, but display a message (and raise an error) if
                # opencv is not available
                self.movie_enabled = HAS_OPENCV

        self.viewer_format = SelectPluginComponent(self,
                                                   items='viewer_format_items',
                                                   selected='viewer_format_selected',
                                                   manual_options=viewer_format_options)

        # NOTE: see self.plugin_table.selected_obj.write.list_formats() for full list of options,
        # although not all support passing overwrite
        plugin_table_format_options = ['ecsv', 'csv', 'fits']
        self.plugin_table_format = SelectPluginComponent(self,
                                                         items='plugin_table_format_items',
                                                         selected='plugin_table_format_selected',
                                                         manual_options=plugin_table_format_options)

        subset_format_options = [{'label': 'fits', 'value': 'fits'},
                                 {'label': 'reg', 'value': 'reg'},
                                 {'label': 'ecsv', 'value': 'ecsv'}]

        if self.config == 'imviz':
            subset_format_options.append({'label': 'stcs', 'value': 'stcs'})

        self.subset_format = SelectPluginComponent(self,
                                                   items='subset_format_items',
                                                   selected='subset_format_selected',
                                                   manual_options=subset_format_options,
                                                   filters=[self._is_valid_item],
                                                   apply_filters_to_manual_options=True)

        if 'specviz' in self.config:
            self.subset_format.selected = 'ecsv'

        dataset_format_options = ['fits']
        self.dataset_format = SelectPluginComponent(self,
                                                    items='dataset_format_items',
                                                    selected='dataset_format_selected',
                                                    manual_options=dataset_format_options)

        plugin_plot_format_options = ['png', 'svg']
        self.plugin_plot_format = SelectPluginComponent(self,
                                                        items='plugin_plot_format_items',
                                                        selected='plugin_plot_format_selected',
                                                        manual_options=plugin_plot_format_options)

        # default selection:
        self.dataset._default_mode = 'empty'
        self.subset._default_mode = 'empty'
        self.plugin_table._default_mode = 'empty'
        self.plugin_plot._default_mode = 'empty'
        self.plugin_plot.select_default()
        self.plugin_table.select_default()
        # viewer last so that the first viewer is the default and all others are empty
        self.viewer.select_default()

        if self.config == "cubeviz":
            self.session.hub.subscribe(self, AddDataMessage, handler=self._on_cubeviz_data_added)  # noqa: E501

        self.session.hub.subscribe(self, SubsetCreateMessage,
                                   handler=self._set_subset_not_supported_msg)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._set_subset_not_supported_msg)
        self.session.hub.subscribe(self, SubsetDeleteMessage,
                                   handler=self._set_subset_not_supported_msg)

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.serverside_enabled = False

        if self.config == 'deconfigged':
            self.observe_traitlets_for_relevancy(
                traitlets_to_observe=['viewer_items',
                                      'dataset_items',
                                      'subset_items',
                                      'plugin_table_items',
                                      'plugin_plot_items'],
                irrelevant_msg_callback=self.relevant_if_any_truthy)

    def _is_valid_item(self, item):
        return self._is_not_stcs(item) or self._is_stcs_region_supported(item)

    def _is_not_stcs(self, item):
        return item.get('label', '') != 'stcs'

    def _is_stcs_region_supported(self, item):
        region = getattr(self.subset, 'selected_spatial_region', None)
        return isinstance(region, (CircleSkyRegion, EllipseSkyRegion))

    def _is_subset_format_supported(self):
        """
        Check if the format of the subset to be exported is supported.
        """
        if self.subset.selected == '' or self.subset.selected is None:
            return

        subset = self.app.get_subsets(self.subset.selected)
        selected = self.subset_format.selected

        self.subset_format_invalid_msg = ''
        is_supported = True

        try:
            is_spectral = self.app._is_subset_spectral(subset[0])
        except KeyError:
            is_spectral = False

        # Disable selecting a bad subset+format combination from the API
        if is_spectral and selected != 'ecsv':
            is_supported = False
        elif not is_spectral and selected == 'ecsv':
            is_supported = False

        # raise vue message
        if not is_supported:
            self.subset_format_invalid_msg = (f"Export of '{self.subset.selected}' "
                                              f"in '{selected}' format is not supported.")

    @observe('subset_selected')
    def _on_subset_selected(self, event):
        if hasattr(self, 'subset_format'):
            self.subset_format._update_items()
            self._is_subset_format_supported()

    # Use an observer function rather than slap the decorator on
    # _is_subset_format_supported for clarity and to follow the
    # convention of the method above.
    @observe('subset_format_selected')
    def _on_subset_format_selected(self, event):
        self._is_subset_format_supported()

    @property
    def user_api(self):
        # TODO: backwards compat for save_figure, save_movie,
        # i_start, i_end, movie_fps, movie_filename
        expose = ['viewer', 'viewer_format',
                  'image_custom_size', 'image_width', 'image_height',
                  'dataset', 'dataset_format',
                  'subset', 'subset_format',
                  'plugin_table', 'plugin_table_format',
                  'plugin_plot', 'plugin_plot_format',
                  'filename', 'export']

        if self.dev_multi_support:
            expose += ['multiselect']

        return PluginUserApi(self, expose=expose)

    def _on_cubeviz_data_added(self, msg):
        # NOTE: This needs revising if we allow loading more than one cube.
        if isinstance(msg.viewer, BqplotImageView):
            if len(msg.data.shape) == 3:
                self.i_end = msg.data.shape[msg.data.meta['spectral_axis_index']] - 1

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
             'plugin_table_selected', 'plugin_plot_selected')
    def _sync_singleselect(self, event):
        if not hasattr(self, 'dataset') or not hasattr(self, 'viewer'):
            # plugin not fully initialized
            return
        # if multiselect is not enabled, only allow a single selection across all select components
        if self.multiselect:
            return
        if event.get('new') in ('', []):
            return
        name = event.get('name')
        for attr in ('viewer_selected', 'dataset_selected', 'subset_selected',
                     'plugin_table_selected', 'plugin_plot_selected'):
            if name != attr:
                setattr(self, attr, '')
            if attr == 'subset_selected':
                self._set_subset_not_supported_msg()
            if attr == 'dataset_selected':
                self._set_dataset_not_supported_msg()

    @observe('viewer_selected', 'viewer_format_selected',
             'dataset_selected', 'dataset_format_selected',
             'subset_selected', 'subset_format_selected',
             'plugin_table_selected', 'plugin_table_format_selected',
             'plugin_plot_selected', 'plugin_plot_format_selected')
    def _set_filename_default(self, *args, **kwargs):
        if not hasattr(self, 'viewer'):
            return
        if self.multiselect:
            raise NotImplementedError("batch export not yet supported")
        if self.viewer_selected:
            self.filename_default = f"{self.viewer_selected}.{self.viewer_format_selected}"  # noqa
        elif self.dataset_selected:
            self.filename_default = f"{self.dataset_selected.replace(' ', '_')}.{self.dataset_format_selected}"  # noqa
        elif self.subset_selected:
            self.filename_default = f"{self.subset_selected.replace(' ', '_')}.{self.subset_format_selected}"  # noqa
        elif self.plugin_table_selected:
            self.filename_default = f"{self.plugin_table_selected.replace(':', '').replace(' ', '_')}.{self.plugin_table_format_selected}"  # noqa
        elif self.plugin_plot_selected:
            self.filename_default = f"{self.plugin_plot_selected.replace(':', '').replace(' ', '_')}.{self.plugin_plot_format_selected}"  # noqa
        else:
            self.filename_default = ''

        # Call to initially set the default filepath
        if hasattr(self, 'viewer_format') and self.filename_default:
            self._normalize_filename(filename=self.filename_default,
                                     filetype=self.viewer_format.selected,
                                     default_path=True)

    @observe('filename_value')
    def _is_filename_changed(self, event):
        # Update the UI Filepath if relative or absolute paths are provided
        # by user via self.filename_value
        expanded_path = os.path.expanduser(self.filename_value)
        abs_path = Path(expanded_path).resolve()
        self.default_filepath = str(abs_path)

        # Clear overwrite warning when user changes filename
        self.overwrite_warn = False

    def _set_subset_not_supported_msg(self, msg=None):
        """
        Check if selected subset is spectral or composite, and warn and
        disable Export button until these are supported.
        """

        if self.subset.selected not in [None, '']:
            try:
                subset = self.app.get_subsets(self.subset.selected)
            except Exception as e:
                self.subset_invalid_msg = f"Export for subset not supported: {e}"
            else:
                if self.subset.selected == '':
                    self.subset_invalid_msg = ''
                    self.subset_format_invalid_msg = ''
                elif self.app._is_subset_spectral(subset[0]):
                    self.subset_invalid_msg = ''
                elif len(subset) > 1:
                    self.subset_invalid_msg = 'Export for composite subsets not yet supported.'
                else:
                    self.subset_invalid_msg = ''
        else:  # no subset selected (can be '' instead of None if previous selection made)
            self.subset_invalid_msg = ''
            self.subset_format_invalid_msg = ''

    def _set_dataset_not_supported_msg(self, msg=None):
        if self.dataset.selected_obj is not None:
            if self.dataset.selected_obj.meta.get("Plugin", None) is None:
                # NOTE: should not be a valid choice due to dataset filters, but we'll include
                # another check here.
                self.data_invalid_msg = "Data export is only available for plugin generated data."
            elif not isinstance(self.dataset.selected_obj, (Spectrum, CCDData)):
                self.data_invalid_msg = "Export is not yet implemented for this type of data"
            elif (data_unit := self.dataset.selected_obj.unit) == u.Unit('DN/s'):
                self.data_invalid_msg = f'Export Disabled: The unit {data_unit} could not be saved in native FITS format.'  # noqa: E501
            else:
                self.data_invalid_msg = ''
        else:
            self.data_invalid_msg = ''

    def _normalize_filename(self, filename=None, filetype=None, overwrite=False, default_path=False):  # noqa: E501
        # Make sure filename is valid and file does not end up in weird places in standalone mode.
        if not filename:
            raise ValueError("Invalid filename")

        if isinstance(filename, str):
            if not filename.endswith(filetype):
                filename += f".{filetype}"
            filename = Path(filename).expanduser()

        filename = filename.resolve()
        filepath = filename.parent
        if filepath and not filepath.is_dir():
            raise ValueError(f"Invalid path={filepath}")
        elif ((not filepath or str(filepath).startswith(".")) and os.environ.get("JDAVIZ_START_DIR", "")):  # noqa: E501 # pragma: no cover
            filename = os.environ["JDAVIZ_START_DIR"] / filename

        # Set the default filepath to inform user where file will be exported to
        if default_path:
            if not filepath.is_absolute():
                abs_path = filepath.resolve()
                self.default_filepath = str(abs_path)
            # set default path for standalone
            if os.environ.get("JDAVIZ_START_DIR", ""):
                self.default_filepath = os.environ["JDAVIZ_START_DIR"]

        if filename.exists() and not overwrite and not default_path:
            self.overwrite_warn = True
        else:
            self.overwrite_warn = False

        return filename

    @with_spinner()
    def export(self, filename=None, show_dialog=None, overwrite=False,
               raise_error_for_overwrite=True):
        """
        Export selected item(s)

        Parameters
        ----------
        filename : str, optional
            If not provided, plugin value will be used.

        show_dialog : bool or `None`
            If `True`, prompts dialog to save PNG/SVG from browser.

        overwrite : bool
            If `True`, silently overwrite an existing file.

        raise_error_for_overwrite : bool
            If `True`, raise exception when ``overwrite=False`` but
            output file already exists. Otherwise, a message will be sent
            to application snackbar instead.
        """
        if self.multiselect:
            raise NotImplementedError("batch export not yet supported")

        filename = filename if filename is not None else self.filename_value

        # at this point, we can assume only a single export is selected
        if len(self.viewer.selected):
            viewer = self.viewer.selected_obj
            if len(self.viewer.selected):
                if self.viewer_invalid_msg != "":
                    raise NotImplementedError(f"Viewer cannot be exported - {self.viewer_invalid_msg}")  # noqa

            viewer = self.viewer.selected_obj

            filetype = self.viewer_format.selected
            filename = self._normalize_filename(filename, filetype, overwrite=overwrite)

            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite=False")
                return

            # temporarily "clean" incompatible marks of unicode characters, etc
            restores = []
            for mark in viewer.figure.marks:
                restore = {}
                if len(getattr(mark, 'text', [])):
                    if not isinstance(mark, ShadowMixin):
                        # if it is shadowing another mark, that will automatically get updated
                        # when the other mark is restored, but we'll still ensure that the mark
                        # is clean of unicode before exporting.
                        restore['text'] = [t for t in mark.text]
                    mark.text = [t.strip() for t in mark.text]
                if len(getattr(mark, 'labels', [])):
                    restore['labels'] = mark.labels[:]
                    mark.labels = [lbl.strip() for lbl in mark.labels]
                restores.append(restore)

            if filetype == "mp4":
                self.save_movie(viewer, filename, filetype,
                                width=f"{self.image_width}px" if self.image_custom_size else None,
                                height=f"{self.image_height}px" if self.image_custom_size else None)
            else:
                self.save_figure(viewer, filename, filetype, show_dialog=show_dialog,
                                 width=f"{self.image_width}px" if self.image_custom_size else None,
                                 height=f"{self.image_height}px" if self.image_custom_size else None)  # noqa

            # restore marks to their original state
            for restore, mark in zip(restores, viewer.figure.marks):
                for k, v in restore.items():
                    setattr(mark, k, v)

        elif len(self.plugin_plot.selected):
            plot = self.plugin_plot.selected_obj._obj
            filetype = self.plugin_plot_format.selected
            filename = self._normalize_filename(filename, filetype, overwrite=overwrite)

            if not plot._plugin.is_active:
                # force an update to the plot.  This requires the plot to have set
                # update_callback when instantiated
                plot._update()

                # create a copy of the widget shown off screen to enable rendering
                # in case one was never created in the parent plugin
                self.plugin_plot_selected_widget = f'IPY_MODEL_{plot.model_id}'

            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite={overwrite}")
                return

            self.save_figure(plot, filename, filetype, show_dialog=show_dialog)

        elif len(self.plugin_table.selected):
            filetype = self.plugin_table_format.selected
            filename = self._normalize_filename(filename, filetype, overwrite=overwrite)
            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite=False")
                return
            self.plugin_table.selected_obj.export_table(filename, overwrite=True)

        elif len(self.subset.selected):
            selected_subset_label = self.subset.selected
            filetype = self.subset_format.selected
            filename = self._normalize_filename(filename, filetype, overwrite=overwrite)
            if self.subset_invalid_msg != '':
                raise NotImplementedError(f'Subset cannot be exported - {self.subset_invalid_msg}')
            elif self.subset_format_invalid_msg:
                raise ValueError(self.subset_format_invalid_msg)

            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite=False")
                return

            if self.subset_format.selected in ('fits', 'reg'):
                self.save_subset_as_region(selected_subset_label, filename)
            elif self.subset_format.selected == 'ecsv':
                self.save_subset_as_table(filename)
            elif self.subset_format.selected == 'stcs':
                self.save_subset_as_stcs(filename)

        elif len(self.dataset.selected):
            filetype = self.dataset_format.selected
            filename = self._normalize_filename(filename, filetype, overwrite=overwrite)
            if self.data_invalid_msg != "":
                raise NotImplementedError(f"Data can not be exported - {self.data_invalid_msg}")
            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite=False")
                return
            self.dataset.selected_obj.write(Path(filename), overwrite=True)
        else:
            raise ValueError("nothing selected for export")

        return filename

    def vue_export_from_ui(self, *args, **kwargs):
        try:
            filename = self.export(show_dialog=True, raise_error_for_overwrite=False)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Export failed with: {e}", sender=self, color="error"))
        else:
            if filename is not None:
                self.hub.broadcast(SnackbarMessage(
                    f"Exported to {filename}", sender=self, color="success"))

    def vue_overwrite_from_ui(self, *args, **kwargs):
        """Attempt to force writing the output if the user confirms the desire to overwrite."""
        try:
            filename = self.export(show_dialog=True, overwrite=True,
                                   raise_error_for_overwrite=False)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Export with overwrite failed with: {e}", sender=self, color="error"))
        else:
            if filename is not None:
                self.hub.broadcast(SnackbarMessage(
                    f"Exported to {filename} (overwrite)", sender=self, color="success"))
            self.overwrite_warn = False

    def save_figure(self, viewer, filename=None, filetype="png", show_dialog=False,
                    width=None, height=None):
        if filename is None:
            filename = self.filename_default

        # viewers in plugins will have viewer.app, other viewers have viewer.jdaviz_app
        if hasattr(viewer, 'jdaviz_app'):
            app = viewer.jdaviz_app
        else:
            app = viewer.app

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

        def get_png(figure):
            if figure._upload_png_callback is not None:
                raise ValueError("previous png export is still in progress. Wait to complete before making another call to save_figure")  # noqa: E501 # pragma: no cover

            figure.get_png_data(on_img_received)

        if (width is not None or height is not None):
            assert width is not None and height is not None, \
                "Both width and height must be provided"
            import ipywidgets as widgets
            from typing import Callable

            def _show_hidden(widget: widgets.Widget, width: str, height: str):
                import ipyvuetify as v
                wrapper_widget = v.Html(
                    children=[
                        v.Html(children=[
                            widget
                        ], tag="div", style_=f"width: {width}; height: {height};")
                    ],
                    tag="div",
                    style_="overflow: hidden; width: 0px; height: 0px"
                    )
                # TODO: we might want to remove it from the DOM
                app.invisible_children = [*app.invisible_children, wrapper_widget]

            def _widget_after_first_display(widget: widgets.Widget, callback: Callable):
                if widget._view_count is None:
                    widget._view_count = 0
                called_callback = False

                def view_count_changed(change):
                    nonlocal called_callback
                    if change["new"] == 1 and not called_callback:
                        called_callback = True
                        callback()
                widget.observe(view_count_changed, "_view_count")

            cloned_viewer = viewer._clone_viewer_outside_app()
            # make sure we will the size of our container which defines the
            # size of the figure
            cloned_viewer.figure.layout.width = "100%"
            cloned_viewer.figure.layout.height = "100%"

            def on_figure_displayed():
                # we need a bit of a delay to ensure the figure is fully displayed
                # maybe this can be fixed on the bqplot side in the future
                def wait_in_other_thread():
                    import time
                    time.sleep(0.2)
                    get_png(cloned_viewer.figure)
                # wait in other thread to avoid blocking the main thread (widgets can update)
                threading.Thread(target=wait_in_other_thread).start()
            _widget_after_first_display(cloned_viewer.figure, on_figure_displayed)
            _show_hidden(cloned_viewer.figure, width, height)
        elif filetype == 'png':
            # NOTE: get_png already check if _upload_png_callback is not None
            get_png(viewer.figure)
        elif filetype == 'svg':
            if viewer.figure._upload_svg_callback is not None:
                raise ValueError("previous svg export is still in progress. Wait to complete before making another call to save_figure") # noqa
            viewer.figure.get_svg_data(on_img_received)
        else:
            raise ValueError(f"Unsupported filetype={filetype} for save_figure")

    @with_spinner('movie_recording')
    def _save_movie(self, viewer, i_start, i_end, fps, filename, rm_temp_files, width, height):
        # NOTE: All the stuff here has to be in the same thread but
        #       separate from main app thread to work.

        if not self.movie_enabled:
            if not HAS_OPENCV:
                raise ImportError("Please install opencv-python")
            raise ValueError("movie support disabled")

        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        orig_slice = viewer.slice
        temp_png_files = []
        i = i_start
        video = None
        slice_plg.value = slice_plg.valid_values_sorted[i_start]

        # TODO: Expose to users?
        i_step = 1  # Need n_frames check if we allow tweaking

        try:
            while i <= i_end:
                if self.movie_interrupt:
                    break

                slice_plg.vue_play_next()
                cur_pngfile = Path(f"._cubeviz_movie_frame_{i}.png")
                # TODO: skip success snackbars when exporting temp movie frames?
                self.save_figure(viewer, filename=cur_pngfile, filetype="png", show_dialog=False,
                                 width=width, height=height)
                temp_png_files.append(cur_pngfile)
                i += i_step

                # Wait for the roundtrip to the frontend to complete.
                while viewer.figure._upload_png_callback is not None:
                    time.sleep(0.05)

            if not self.movie_interrupt:
                # Grab frame size.
                frame_shape = cv2.imread(temp_png_files[0]).shape
                frame_size = (frame_shape[1], frame_shape[0])

                video = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size, True)  # noqa: E501
                for cur_pngfile in temp_png_files:
                    video.write(cv2.imread(cur_pngfile))
        except Exception as err:
            self.hub.broadcast(SnackbarMessage(
                f"Error saving {filename}: {err!r}", sender=self, color="error"))
        finally:
            cv2.destroyAllWindows()
            if video:
                video.release()
            slice_plg.value = slice_plg.valid_values_sorted[orig_slice]

        if rm_temp_files or self.movie_interrupt:
            for cur_pngfile in temp_png_files:
                if os.path.exists(cur_pngfile):
                    os.remove(cur_pngfile)

        if self.movie_interrupt:
            if os.path.exists(filename):
                os.remove(filename)
            self.movie_interrupt = False

    def save_movie(self, viewer, filename, filetype, i_start=None, i_end=None, fps=None,
                   rm_temp_files=True, width=None, height=None):
        """Save selected slices as a movie.

        This method creates a PNG file per frame (``._cubeviz_movie_frame_<n>.png``)
        in the working directory before stitching all the frames into a movie.
        Please make sure you have sufficient memory for this operation.
        PNG files are deleted after the movie is created unless otherwise specified.
        If another PNG file with the same name already exists, it will be silently replaced.

        Parameters
        ----------
        i_start, i_end : int or `None`
            Slices to record; each slice will be a frame in the movie.
            If not given, it is obtained from plugin inputs.
            Unlike Python indexing, ``i_end`` is inclusive.
            Wrapping and reverse indexing are not supported.

        fps : float or `None`
            Frame rate in frames per second (FPS).
            If not given, it is obtained from plugin inputs.

        filename : str or `None`
            Filename for the movie to be recorded. Include path if necessary.
            If not given, it is obtained from plugin inputs.
            If another file with the same name already exists, it will be silently replaced.

        filetype : {'mp4', `None`}
            Currently only MPEG-4 is supported. This keyword is reserved for future support
            of other format(s).

        rm_temp_files : bool
            Remove temporary PNG files after movie creation. Default is `True`.

        width : str, optional
            Width of the exported image. Required if height is provided.

        height : str, optional
            Height of the exported image. Required if width is provided.

        Returns
        -------
        out_filename : str
            The absolute path to the actual output file.

        """
        if self.config != "cubeviz":
            raise NotImplementedError(f"save_movie is not available for config={self.config}")

        if not HAS_OPENCV:
            raise ImportError("Please install opencv-python to save cube as movie.")

        if filetype != "mp4":
            raise NotImplementedError(f"filetype={filetype} not supported")

        if viewer.shape is None:
            raise ValueError("Selected viewer has no display shape.")

        if fps is None:
            fps = float(self.movie_fps)
        if fps <= 0:
            raise ValueError("Invalid frame rate, must be positive non-zero value.")

        if i_start is None:
            i_start = int(self.i_start)

        if i_end is None:
            i_end = int(self.i_end)

        # No wrapping. Forward only.
        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        if i_start < 0:  # pragma: no cover
            i_start = 0
        max_slice = len(slice_plg.valid_values_sorted) - 1
        if i_end > max_slice:  # pragma: no cover
            i_end = max_slice
        if i_end <= i_start:
            raise ValueError(f"No frames to write: i_start={i_start}, i_end={i_end}")

        threading.Thread(
            target=lambda: self._save_movie(viewer, i_start, i_end, fps, filename, rm_temp_files,
                                            width, height)
        ).start()

        return filename

    def save_subset_as_stcs(self, filename):
        """
        Save a subset region to a text file in STC-S format.

        Currently implemented for Circle and Ellipse sky regions only.

        Parameters
        ----------
        filename : str
            Write the STC-S region to a text file with this name.

        Raises
        ------
        RuntimeError
            If data is not aligned by WCS, which is required for STC-S export.
        """
        align_by = getattr(self.app, '_align_by', None)
        if align_by != 'wcs':
            raise RuntimeError("Please link datasets by WCS first using the Orientation plugin.")

        region = self.app.get_subsets(subset_name=self.subset.selected,
                                      include_sky_region=True)[0]['sky_region']

        stcs_str = region2stcs_string(region)

        with open(filename, 'w') as f:
            f.write(stcs_str)

    def save_subset_as_region(self, selected_subset_label, filename):
        """
        Save a subset to file as a Region object in the working directory.
        Currently only enabled for non-composite spatial subsets. Can be saved
        as a .fits or .reg file. If link type is currently set to 'pixel',
        then a pixel region will be saved. If link type is 'wcs', then a sky
        region will be saved. If a file with the same name already exists in the
        working directory, it will be overwriten.
        """

        # type of region saved depends on link type
        align_by = getattr(self.app, '_align_by', None)

        region = self.app.get_subsets(subset_name=selected_subset_label,
                                      include_sky_region=align_by == 'wcs')

        region = region[0][f'{"sky_" if align_by == "wcs" else ""}region']

        region.write(str(filename), overwrite=True)

    def save_subset_as_table(self, filename):
        region = self.app.get_subsets(subset_name=self.subset.selected)
        region.write(str(filename))

    def vue_interrupt_recording(self, *args):  # pragma: no cover
        self.movie_interrupt = True
        # TODO: this will need updating when batch/multiselect support is added
        self.hub.broadcast(SnackbarMessage(
            f"Movie recording interrupted by user, {self.filename_value} will be deleted.",
            sender=self, color="warning"))
