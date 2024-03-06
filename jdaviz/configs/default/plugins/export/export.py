import os
from pathlib import Path
from traitlets import Any, Bool, List, Unicode, observe
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.custom_traitlets import FloatHandleEmpty, IntHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, SelectPluginComponent,
                                        ViewerSelectMixin, DatasetMultiSelectMixin,
                                        SubsetSelectMixin, MultiselectMixin, with_spinner)
from jdaviz.core.events import AddDataMessage, SnackbarMessage
from jdaviz.core.user_api import PluginUserApi

try:
    import cv2
except ImportError:
    HAS_OPENCV = False
else:
    import threading
    import time
    HAS_OPENCV = True

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

    # For Cubeviz movie.
    i_start = IntHandleEmpty(0).tag(sync=True)
    i_end = IntHandleEmpty(0).tag(sync=True)
    movie_fps = FloatHandleEmpty(5.0).tag(sync=True)
    movie_recording = Bool(False).tag(sync=True)
    movie_interrupt = Bool(False).tag(sync=True)

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
        if (self.config == 'cubeviz'
                and not self.app.state.settings.get('server_is_remote', False)
                and HAS_OPENCV):
            # when the server is remote, saving the movie in python would save on the server, not
            # on the user's machine, so movie support in cubeviz is not exposed
            viewer_format_options += ['mp4']

        self.viewer_format = SelectPluginComponent(self,
                                                   items='viewer_format_items',
                                                   selected='viewer_format_selected',
                                                   manual_options=viewer_format_options)

        # default selection:
        self.dataset._default_mode = 'empty'
        self.viewer.select_default()
        self.filename = f"{self.app.config}_export"

        if self.config == "cubeviz":
            self.session.hub.subscribe(self, AddDataMessage, handler=self._on_cubeviz_data_added)  # noqa: E501

    @property
    def user_api(self):
        # TODO: backwards compat for save_figure, save_movie,
        # i_start, i_end, movie_fps, movie_filename
        # TODO: expose export method once API is finalized
        expose = ['viewer', 'viewer_format', 'filename', 'export']

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

    def _on_cubeviz_data_added(self, msg):
        # NOTE: This needs revising if we allow loading more than one cube.
        if isinstance(msg.viewer, BqplotImageView):
            if len(msg.data.shape) == 3:
                self.i_end = msg.data.shape[-1] - 1  # Same as max_slice in Slice plugin

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
        Export selected item(s)

        Parameters
        ----------
        filename : str, optional
            If not provided, plugin value will be used.
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

        if filetype == "mp4":
            self.save_movie(viewer, filename, filetype)
        else:
            self.save_figure(viewer, filename, filetype, show_dialog=show_dialog)

    def vue_export_from_ui(self, *args, **kwargs):
        try:
            self.export(show_dialog=True)
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Export failed with: {e}", sender=self, color="error"))

    def save_figure(self, viewer, filename=None, filetype="png", show_dialog=False):
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

    @with_spinner('movie_recording')
    def _save_movie(self, viewer, i_start, i_end, fps, filename, rm_temp_files):
        # NOTE: All the stuff here has to be in the same thread but
        #       separate from main app thread to work.

        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        orig_slice = slice_plg.slice
        temp_png_files = []
        i = i_start
        video = None

        # TODO: Expose to users?
        i_step = 1  # Need n_frames check if we allow tweaking

        try:
            while i <= i_end:
                if self.movie_interrupt:
                    break

                slice_plg._on_slider_updated({'new': i})
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

        # Make sure file does not end up in weird places in standalone mode.
        if filename is None:
            raise ValueError("Invalid filename")
        path = filename.parent
        if path and not path.exists():
            raise ValueError(f"Invalid path={path}")
        elif (not path or str(path).startswith("..")) and os.environ.get("JDAVIZ_START_DIR", ""):  # noqa: E501 # pragma: no cover
            filename = os.environ["JDAVIZ_START_DIR"] / filename

        if i_start is None:
            i_start = int(self.i_start)

        if i_end is None:
            i_end = int(self.i_end)

        # No wrapping. Forward only.
        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        if i_start < 0:  # pragma: no cover
            i_start = 0
        if i_end > slice_plg.max_slice:  # pragma: no cover
            i_end = slice_plg.max_slice
        if i_end <= i_start:
            raise ValueError(f"No frames to write: i_start={i_start}, i_end={i_end}")

        filename = str(filename.resolve())
        threading.Thread(
            target=lambda: self._save_movie(viewer, i_start, i_end, fps, filename, rm_temp_files)
        ).start()

        return filename

    def vue_interrupt_recording(self, *args):  # pragma: no cover
        self.movie_interrupt = True
        # TODO: this will need updating when batch/multiselect support is added
        self.hub.broadcast(SnackbarMessage(
            f"Movie recording interrupted by user, {self.filename} will be deleted.",
            sender=self, color="warning"))
