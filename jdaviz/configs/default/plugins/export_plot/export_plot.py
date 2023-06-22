import os

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, ViewerSelectMixin
from jdaviz.core.user_api import PluginUserApi

try:
    import cv2
except ImportError:
    HAS_OPENCV = False
else:
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

    @property
    def user_api(self):
        if self.config == "cubeviz":
            return PluginUserApi(self, expose=('viewer', 'save_figure', 'save_movie'))
        return PluginUserApi(self, expose=('viewer', 'save_figure'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def save_movie(self, i_start, i_end, filename=None, filetype=None, rm_temp_files=True):
        """``i`` start/end control the frames being written out.
        ``i_end`` is inclusive. This method creates a bunch of
        PNG files (one per frame) and then deletes them after stitching
        the video.
        """
        if not HAS_OPENCV:
            raise ImportError("Please install opencv-python to save cube as movie.")

        if self.config != "cubeviz":
            raise NotImplementedError(f"save_movie is not available for config={self.config}")

        if filetype is None:
            if filename is not None and '.' in filename:
                filetype = filename.split('.')[-1]
            else:
                # default to MPEG-4
                filetype = "mp4"

        if filetype != "mp4":
            raise NotImplementedError(f"filetype={filetype} not supported")

        viewer = self.viewer.selected_obj
        if viewer.shape is None:
            raise ValueError("Selected viewer has no display shape.")

        if filename is None:
            filename = f"mymovie.{filetype}"

        slice_plg = self.app._jdaviz_helper.plugins["Slice"]._obj
        orig_slice = slice_plg.slice
        ts = float(slice_plg.play_interval) * 1e-3  # ms to s
        temp_png_files = []

        # TODO: Expose to users?
        frame_size = viewer.shape[::-1]  # nx, ny
        fps = 5  # This is arbitrary
        i_step = 1  # Need n_frames check if we allow tweaking

        # No wrapping. Forward only.
        if i_start < 0:
            i_start = 0
        if i_end > slice_plg.max_value:
            i_end = slice_plg.max_value
        if i_end <= i_start:
            raise ValueError(f"No frames to write: i_start={i_start}, i_end={i_end}")

        video = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), fps, frame_size, True)
        i = i_start

        try:
            self.app.loading = True  # Grays out the app

            while i <= i_end:
                slice_plg._on_slider_updated({'new': i})
                cur_pngfile = f"._cubeviz_movie_frame_{i}.png"

                # FIXME: bqplot stuck after first frame!
                # If we can fix this, maybe we can have callback to video.write and don't need PNG files.
                self.save_figure(filename=cur_pngfile, filetype="png")

                temp_png_files.append(cur_pngfile)
                i += i_step
                time.sleep(ts)  # Avoid giving user epilepsy

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

    def vue_save_movie(self, filetype):
        """
        Callback for save movie events in the front end viewer toolbars. Uses
        the bqplot.Figure save methods.
        """
        self.save_movie(filetype=filetype)
