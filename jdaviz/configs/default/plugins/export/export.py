import os
import time
from pathlib import Path
from traitlets import Bool, List, Unicode, observe
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.custom_traitlets import FloatHandleEmpty, IntHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, SelectPluginComponent,
                                        ViewerSelectMixin, DatasetMultiSelectMixin,
                                        SubsetSelectMixin, PluginTableSelectMixin,
                                        PluginPlotSelectMixin,
                                        MultiselectMixin, with_spinner)
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage

from jdaviz.core.events import AddDataMessage, SnackbarMessage
from jdaviz.core.user_api import PluginUserApi
from specutils import Spectrum1D
from astropy import units as u
from astropy.nddata import CCDData

try:
    import cv2
except ImportError:
    HAS_OPENCV = False
else:
    import threading
    HAS_OPENCV = True

__all__ = ['Export']


@tray_registry('export', label="Export")
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

    plugin_table_format_items = List().tag(sync=True)
    plugin_table_format_selected = Unicode().tag(sync=True)

    subset_format_items = List().tag(sync=True)
    subset_format_selected = Unicode().tag(sync=True)

    dataset_format_items = List().tag(sync=True)
    dataset_format_selected = Unicode().tag(sync=True)

    plugin_plot_format_items = List().tag(sync=True)
    plugin_plot_format_selected = Unicode().tag(sync=True)

    filename = Unicode().tag(sync=True)

    # if selected subset is spectral or composite, display message and disable export
    subset_invalid_msg = Unicode().tag(sync=True)
    data_invalid_msg = Unicode().tag(sync=True)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NOTE: if adding export support for non-plugin products, also update the language
        # in the UI as well as in _set_dataset_not_supported_msg
        self.dataset.filters = ['is_not_wcs_only', 'not_child_layer',
                                'from_plugin']

        # NOTE: if/when adding support for spectral subsets, update the languange in the UI
        self.subset.filters = ['is_spatial']

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
                                                         items='plugin-table_format_items',
                                                         selected='plugin_table_format_selected',
                                                         manual_options=plugin_table_format_options)

        subset_format_options = ['fits', 'reg']
        self.subset_format = SelectPluginComponent(self,
                                                   items='subset_format_items',
                                                   selected='subset_format_selected',
                                                   manual_options=subset_format_options)

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
        self.filename = f"{self.app.config}_export"

        if self.config == "cubeviz":
            self.session.hub.subscribe(self, AddDataMessage, handler=self._on_cubeviz_data_added)  # noqa: E501

        self.session.hub.subscribe(self, SubsetCreateMessage,
                                   handler=self._set_subset_not_supported_msg)
        self.session.hub.subscribe(self, SubsetUpdateMessage,
                                   handler=self._set_subset_not_supported_msg)
        self.session.hub.subscribe(self, SubsetDeleteMessage,
                                   handler=self._set_subset_not_supported_msg)

    @property
    def user_api(self):
        # TODO: backwards compat for save_figure, save_movie,
        # i_start, i_end, movie_fps, movie_filename
        # TODO: expose export method once API is finalized

        expose = ['viewer', 'viewer_format',
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
                self.i_end = msg.data.shape[-1] - 1

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
            # plugin not fully intialized
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
            elif self.config == "cubeviz" and attr == "viewer_selected":
                self._disable_viewer_format_combo(event)

    @observe('viewer_format_selected')
    def _disable_viewer_format_combo(self, event):
        if (self.config == "cubeviz" and self.viewer_selected == "spectrum-viewer"
                and self.viewer_format_selected == "png"):
            msg = "Exporting the spectrum viewer as a PNG in Cubeviz is not yet supported"
        else:
            msg = ""
        self.viewer_invalid_msg = msg

    @observe('filename')
    def _is_filename_changed(self, event):
        # Clear overwrite warning when user changes filename
        self.overwrite_warn = False

    def _set_subset_not_supported_msg(self, msg=None):
        """
        Check if selected subset is spectral or composite, and warn and
        disable Export button until these are supported.
        """

        if self.subset.selected is not None:
            subset = self.app.get_subsets(self.subset.selected)
            if self.subset.selected == '':
                self.subset_invalid_msg = ''
            elif self.app._is_subset_spectral(subset[0]):
                self.subset_invalid_msg = 'Export for spectral subsets not yet supported.'
            elif len(subset) > 1:
                self.subset_invalid_msg = 'Export for composite subsets not yet supported.'
            else:
                self.subset_invalid_msg = ''
        else:  # no subset selected (can be '' instead of None if previous selection made)
            self.subset_invalid_msg = ''

    def _set_dataset_not_supported_msg(self, msg=None):
        if self.dataset.selected_obj is not None:
            if self.dataset.selected_obj.meta.get("Plugin", None) is None:
                # NOTE: should not be a valid choice due to dataset filters, but we'll include
                # another check here.
                self.data_invalid_msg = "Data export is only available for plugin generated data."
            elif not isinstance(self.dataset.selected_obj, (Spectrum1D, CCDData)):
                self.data_invalid_msg = "Export is not yet implemented for this type of data"
            elif (data_unit := self.dataset.selected_obj.unit) == u.Unit('DN/s'):
                self.data_invalid_msg = f'Export Disabled: The unit {data_unit} could not be saved in native FITS format.'  # noqa: E501
            else:
                self.data_invalid_msg = ''
        else:
            self.data_invalid_msg = ''

    def _normalize_filename(self, filename=None, filetype=None, overwrite=False):
        # Make sure filename is valid and file does not end up in weird places in standalone mode.
        if not filename:
            raise ValueError("Invalid filename")

        if isinstance(filename, str):
            if not filename.endswith(filetype):
                filename += f".{filetype}"
            filename = Path(filename).expanduser()

        filepath = filename.parent
        if filepath and not filepath.is_dir():
            raise ValueError(f"Invalid path={filepath}")
        elif ((not filepath or str(filepath).startswith(".")) and os.environ.get("JDAVIZ_START_DIR", "")):  # noqa: E501 # pragma: no cover
            filename = os.environ["JDAVIZ_START_DIR"] / filename

        if filename.exists() and not overwrite:
            self.overwrite_warn = True
        else:
            self.overwrite_warn = False

        return str(filename)

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

        filename = filename if filename is not None else self.filename

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

            if filetype == "mp4":
                self.save_movie(viewer, filename, filetype)
            else:
                self.save_figure(viewer, filename, filetype, show_dialog=show_dialog)

        elif len(self.plugin_plot.selected):
            plot = self.plugin_plot.selected_obj._obj
            filetype = self.plugin_plot_format.selected

            if len(filename):
                if not filename.endswith(filetype):
                    filename += f".{filetype}"
                filename = Path(filename).expanduser()
            else:
                filename = None

            with plot._plugin.as_active():
                # NOTE: could still take some time for the plot itself to update,
                # for now we'll hardcode a short amount of time for the plot to render any updates
                time.sleep(0.2)
                self.save_figure(plot, filename, filetype, show_dialog=show_dialog)

        elif len(self.plugin_table.selected):
            filetype = self.plugin_table_format.selected
            filename = self._normalize_filename(filename, filetype)
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
                raise NotImplementedError(f'Subset can not be exported - {self.subset_invalid_msg}')
            if self.overwrite_warn and not overwrite:
                if raise_error_for_overwrite:
                    raise FileExistsError(f"{filename} exists but overwrite=False")
                return
            self.save_subset_as_region(selected_subset_label, filename)

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

    def save_figure(self, viewer, filename=None, filetype="png", show_dialog=False):

        if filetype == "png":
            if filename is None or show_dialog:
                viewer.figure.save_png(str(filename) if filename is not None else None)
            else:
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

    @with_spinner('movie_recording')
    def _save_movie(self, viewer, i_start, i_end, fps, filename, rm_temp_files):
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

        # TODO: Expose to users?
        i_step = 1  # Need n_frames check if we allow tweaking

        try:
            while i <= i_end:
                if self.movie_interrupt:
                    break

                slice_plg.vue_play_next()
                cur_pngfile = Path(f"._cubeviz_movie_frame_{i}.png")
                # TODO: skip success snackbars when exporting temp movie frames?
                self.save_figure(viewer, filename=cur_pngfile, filetype="png", show_dialog=False)
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
            slice_plg._on_slider_updated({'new': orig_slice})

        if rm_temp_files or self.movie_interrupt:
            for cur_pngfile in temp_png_files:
                if os.path.exists(cur_pngfile):
                    os.remove(cur_pngfile)

        if self.movie_interrupt:
            if os.path.exists(filename):
                os.remove(filename)
            self.movie_interrupt = False

    def save_movie(self, viewer, filename, filetype, i_start=None, i_end=None, fps=None,
                   rm_temp_files=True):
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

        filename = str(filename.resolve())
        threading.Thread(
            target=lambda: self._save_movie(viewer, i_start, i_end, fps, filename, rm_temp_files)
        ).start()

        return filename

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
        link_type = getattr(self.app, '_link_type', None)

        region = self.app.get_subsets(subset_name=selected_subset_label,
                                      include_sky_region=link_type == 'wcs')

        region = region[0][f'{"sky_" if link_type == "wcs" else ""}region']

        region.write(filename, overwrite=True)

    def vue_interrupt_recording(self, *args):  # pragma: no cover
        self.movie_interrupt = True
        # TODO: this will need updating when batch/multiselect support is added
        self.hub.broadcast(SnackbarMessage(
            f"Movie recording interrupted by user, {self.filename} will be deleted.",
            sender=self, color="warning"))
