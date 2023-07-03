import os

from glue_jupyter.bqplot.image import BqplotImageView
from traitlets import Any, Bool, Unicode

from jdaviz.core.custom_traitlets import FloatHandleEmpty, IntHandleEmpty
from jdaviz.core.events import AddDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi

try:
    import cv2
except ImportError:
    HAS_OPENCV = False
else:
    import threading
    import time
    HAS_OPENCV = True

__all__ = ['ExportViewer']


@tray_registry('g-export-plot', label="Export Plot")
class ExportViewer(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Export Plot Plugin Documentation <imviz-export-plot>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
      Viewer to select for exporting the figure image.
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`save_figure`
    * :meth:`save_movie` (Cubeviz only)
    * `i_start` (Cubeviz only)
    * `i_end` (Cubeviz only)
    * `movie_fps` (Cubeviz only)
    * `movie_filename` (Cubeviz only)
    """
    template_file = __file__, "export_plot.vue"

    # For Cubeviz movie.
    i_start = IntHandleEmpty(0).tag(sync=True)
    i_end = IntHandleEmpty(0).tag(sync=True)
    movie_fps = FloatHandleEmpty(5.0).tag(sync=True)
    movie_filename = Any("mymovie.mp4").tag(sync=True)
    movie_msg = Unicode("").tag(sync=True)
    movie_recording = Bool(False).tag(sync=True)
    movie_interrupt = Bool(False).tag(sync=True)

    @property
    def user_api(self):
        if self.config == "cubeviz":
            return PluginUserApi(self, expose=('viewer', 'save_figure', 'save_movie', 'i_start',
                                               'i_end', 'movie_fps', 'movie_filename'))
        return PluginUserApi(self, expose=('viewer', 'save_figure'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config == "cubeviz":
            if HAS_OPENCV:
                self.session.hub.subscribe(self, AddDataMessage, handler=self._on_cubeviz_data_added)  # noqa: E501
            else:
                # NOTE: HTML tags do not work here.
                self.movie_msg = 'Please install opencv-python to use this feature.'

    def _on_cubeviz_data_added(self, msg):
        # NOTE: This needs revising if we allow loading more than one cube.
        if isinstance(msg.viewer, BqplotImageView):
            if len(msg.data.shape) == 3:
                self.i_end = msg.data.shape[-1] - 1  # Same as max_value in Slice plugin

    def save_figure(self, filename=None, filetype=None):
        """
        Save the figure to an image with a provided filename or through an interactive save dialog.

        If ``filetype`` is 'png' (or defaults to 'png' based on ``filename``), the interactive save
        dialog will be bypassed (this is not supported for 'svg').

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
            if filename is None:
                viewer.figure.save_png()
            else:
                # support writing without save dialog
                # https://github.com/bqplot/bqplot/pull/1397
                def on_img_received(data):
                    with open(os.path.expanduser(filename), 'bw') as f:
                        f.write(data)
                viewer.figure.get_png_data(on_img_received)
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

    def _save_movie(self, i_start, i_end, fps, filename, rm_temp_files):
        # NOTE: All the stuff here has to be in the same thread but
        #       separate from main app thread to work.

        viewer = self.viewer.selected_obj
        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        orig_slice = slice_plg.slice
        temp_png_files = []
        i = i_start
        video = None

        # TODO: Expose to users?
        i_step = 1  # Need n_frames check if we allow tweaking

        try:
            self.movie_recording = True

            while i <= i_end:
                if self.movie_interrupt:
                    break

                slice_plg._on_slider_updated({'new': i})
                cur_pngfile = f"._cubeviz_movie_frame_{i}.png"
                self.save_figure(filename=cur_pngfile, filetype="png")
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
        finally:
            cv2.destroyAllWindows()
            if video:
                video.release()
            slice_plg._on_slider_updated({'new': orig_slice})
            self.movie_recording = False

        if rm_temp_files or self.movie_interrupt:
            for cur_pngfile in temp_png_files:
                if os.path.exists(cur_pngfile):
                    os.remove(cur_pngfile)

        if self.movie_interrupt:
            if os.path.exists(filename):
                os.remove(filename)
            self.movie_interrupt = False

    def save_movie(self, i_start=None, i_end=None, fps=None, filename=None, filetype=None,
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

        if filetype is None:
            if filename is not None and '.' in filename:
                filetype = filename.split('.')[-1]
            else:
                # default to MPEG-4
                filetype = "mp4"

        if filetype != "mp4":
            raise NotImplementedError(f"filetype={filetype} not supported")

        viewer = self.viewer.selected_obj
        if not isinstance(viewer, BqplotImageView):  # Profile viewer in glue-jupyter cannot do this
            raise TypeError(f"Movie for {viewer.__class__.__name__} is not supported.")
        if viewer.shape is None:
            raise ValueError("Selected viewer has no display shape.")

        if fps is None:
            fps = float(self.movie_fps)
        if fps <= 0:
            raise ValueError("Invalid frame rate, must be positive non-zero value.")

        if filename is None:
            if self.movie_filename:
                filename = self.movie_filename
            else:
                raise ValueError("Invalid filename.")

        # Make sure file does not end up in weird places in standalone mode.
        path = os.path.dirname(filename)
        if path and not os.path.exists(path):
            raise ValueError(f"Invalid path={path}")
        elif (not path or path.startswith("..")) and os.environ.get("JDAVIZ_START_DIR", ""):  # noqa: E501 # pragma: no cover
            filename = os.path.join(os.environ["JDAVIZ_START_DIR"], filename)

        if i_start is None:
            i_start = int(self.i_start)

        if i_end is None:
            i_end = int(self.i_end)

        # No wrapping. Forward only.
        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        if i_start < 0:  # pragma: no cover
            i_start = 0
        if i_end > slice_plg.max_value:  # pragma: no cover
            i_end = slice_plg.max_value
        if i_end <= i_start:
            raise ValueError(f"No frames to write: i_start={i_start}, i_end={i_end}")

        threading.Thread(
            target=lambda: self._save_movie(i_start, i_end, fps, filename, rm_temp_files)
        ).start()

        return os.path.abspath(filename)

    def vue_save_movie(self, filetype):  # pragma: no cover
        """
        Callback for save movie events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        try:
            filename = self.save_movie(filetype=filetype)
        except Exception as err:  # pragma: no cover
            self.hub.broadcast(SnackbarMessage(
                f"Error saving {self.movie_filename}: {err!r}", sender=self, color="error"))
        else:
            # Let the user know where we saved the file.
            # NOTE: Because of threading, this will be emitted even as movie as recording.
            self.hub.broadcast(SnackbarMessage(
                f"Movie being saved to {filename} for slices {self.i_start} to {self.i_end}, "
                f"inclusive, at {self.movie_fps} FPS.",
                sender=self, color="success"))

    def vue_interrupt_recording(self, *args):  # pragma: no cover
        self.movie_interrupt = True
        self.hub.broadcast(SnackbarMessage(
            f"Movie recording interrupted by user, {self.movie_filename} will be deleted.",
            sender=self, color="warning"))
