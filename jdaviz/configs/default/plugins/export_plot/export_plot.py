import os

from glue_jupyter.bqplot.image import BqplotImageView
from traitlets import Any

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
    """
    template_file = __file__, "export_plot.vue"

    # For Cubeviz movie.
    i_start = Any(0).tag(sync=True)
    i_end = Any(0).tag(sync=True)
    movie_fps = Any(5.0).tag(sync=True)
    movie_filename = Any("mymovie.mp4").tag(sync=True)

    @property
    def user_api(self):
        if self.config == "cubeviz":
            return PluginUserApi(self, expose=('viewer', 'save_figure', 'save_movie'))
        return PluginUserApi(self, expose=('viewer', 'save_figure'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.config == "cubeviz":
            self.session.hub.subscribe(self, AddDataMessage, handler=self._on_cubeviz_data_added)

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
        self.app.loading = True  # Grays out the app
        viewer = self.viewer.selected_obj
        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        orig_slice = slice_plg.slice
        ts = float(slice_plg.play_interval) * 1e-3  # ms to s
        temp_png_files = []

        # TODO: Expose to users?
        i_step = 1  # Need n_frames check if we allow tweaking

        # No wrapping. Forward only.
        if i_start < 0:
            i_start = 0
        if i_end > slice_plg.max_value:
            i_end = slice_plg.max_value
        if i_end <= i_start:
            self.app.loading = False
            raise ValueError(f"No frames to write: i_start={i_start}, i_end={i_end}")


        i = i_start
        while i <= i_end:
            slice_plg._on_slider_updated({'new': i})
            cur_pngfile = f"._cubeviz_movie_frame_{i}.png"
            self.save_figure(filename=cur_pngfile, filetype="png")
            temp_png_files.append(cur_pngfile)
            i += i_step
            time.sleep(ts)  # Avoid giving user epilepsy

            # Wait for the roundtrip to the frontend to complete in case the epilepsy
            # mitigating sleep wasn't long enough
            while viewer.figure._upload_png_callback is not None:
                time.sleep(ts)

        # Grab frame size.
        frame_shape = cv2.imread(temp_png_files[0]).shape
        frame_size = (frame_shape[1], frame_shape[0])

        try:
            video = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size, True)  # noqa: E501
            for cur_pngfile in temp_png_files:
                video.write(cv2.imread(cur_pngfile))
        finally:
            cv2.destroyAllWindows()
            video.release()
            slice_plg._on_slider_updated({'new': orig_slice})
            self.app.loading = False

        if rm_temp_files:
            for cur_pngfile in temp_png_files:
                os.remove(cur_pngfile)

    def save_movie(self, i_start, i_end, fps=5, filename=None, filetype=None, rm_temp_files=True):
        """Save selected slices as a movie.

        This method creates a PNG file per frame (``._cubeviz_movie_frame_<n>.png``)
        in the working directory before stitching all the frames into a movie.
        Please make sure you have sufficient memory for this operation.
        PNG files are deleted after the movie is created unless otherwise specified.
        If another PNG file with the same name already exists, it will be silently replaced.

        Movie is written out with frame rate of 5 frames per second (FPS).

        Parameters
        ----------
        i_start, i_end : int
            Slices to record; each slice will be a frame in the movie.
            Unlike Python indexing, ``i_end`` is inclusive.
            Wrapping and reverse indexing are not supported.

        fps : float
            Frame rate in frames per second (FPS). Default is 5.

        filename : str or `None`
            Filename for the movie to be recorded. Include path if necessary.
            If not given, it will be named ``mymovie.mp4`` in the working directory.
            If another file with the same name already exists, it will be silently replaced.

        filetype : {'mp4', `None`}
            Currently only MPEG-4 is supported. This keyword is reserved for future support
            of other format(s).

        rm_temp_files : bool
            Remove temporary PNG files after movie creation. Default is `True`.

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

        if fps <= 0:
            raise ValueError("Invalid frame rate, must be positive non-zero value.")

        if filename is None:
            filename = f"mymovie.{filetype}"

        threading.Thread(
            target=lambda: self._save_movie(i_start, i_end, fps, filename, rm_temp_files)
        ).start()

    def vue_save_movie(self, filetype, debug=False):
        """
        Callback for save movie events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        try:
            i_start = int(self.i_start)
            i_end = int(self.i_end)
            fps = float(self.movie_fps)
            filename = self.movie_filename

            # Make sure file does not end up in weird places in standalone mode.
            path = os.path.dirname(filename)
            if path and not os.path.exists(path):
                raise ValueError(f"Invalid path={path}")
            elif not path and os.environ.get("JDAVIZ_START_DIR", ""):  # pragma: no cover
                filename = os.path.join(os.environ["JDAVIZ_START_DIR"], filename)

            self.save_movie(i_start, i_end, fps=fps, filename=filename, filetype=filetype)
        except Exception as err:  # pragma: no cover
            if debug:  # For debugging and testing
                raise
            self.hub.broadcast(SnackbarMessage(
                f"Error saving {filename}: {err!r}", sender=self, color="error"))
        else:
            # Let the user know where we saved the file.
            self.hub.broadcast(SnackbarMessage(
                f"Movie saved to {os.path.abspath(filename)} "
                f"for slices {i_start} to {i_end}, inclusive, at {fps:.1f} FPS.",
                sender=self, color="success"))
