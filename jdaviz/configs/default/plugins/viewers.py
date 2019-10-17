from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.matplotlib.profile import ProfileJupyterViewer
from glue_jupyter.utils import validate_data_argument

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import viewers


@viewers("profile-1d", label="Profile 1D")
class Profile1DViewer:
    def __init__(self, *, hub=None, data=None, x_attr=None, widget='bqplot', show=True):
        """
        Open an interactive 1d profile viewer.

        Parameters
        ----------
        data : str or `~glue.core.data.Data`, optional
            The initial dataset to show in the viewer. Additional
            datasets can be added later using the ``add_data`` method on
            the viewer object.
        x_attr : str or `~glue.core.component_id.ComponentID`, optional
            The attribute to show on the x axis. This should be a pixel or
            world coordinate `~glue.core.component_id.ComponentID`.
        widget : {'bqplot', 'matplotlib'}
            Whether to use bqplot or Matplotlib as the front-end.
        show : bool, optional
            Whether to show the view immediately (`True`) or whether to only
            show it later if the ``show()`` method is called explicitly
            (`False`).
        """
        if widget == 'bqplot':
            viewer_cls = BqplotProfileView
        elif widget == 'matplotlib':
            viewer_cls = ProfileJupyterViewer
        else:
            raise ValueError("Widget type should be 'matplotlib'")

        data = validate_data_argument(self.data_collection, data)

        new_viewer_message = NewViewerMessage(viewer_cls, data=data, x_attr=x_attr)

        hub.broadcast(new_viewer_message)

        # view = self.new_data_viewer(viewer_cls, data=data, show=show)
        #
        # if x is not None:
        #     x = data.id[x]
        #     view.state.x_att = x
        #
        # return view


@viewers("imshow", label="Image 2D")
class ImageViewer:
    def __init__(self, *, hub=None, data=None, x_attr=None, widget='bqplot', show=True):
        """
        Open an interactive 1d profile viewer.

        Parameters
        ----------
        data : str or `~glue.core.data.Data`, optional
            The initial dataset to show in the viewer. Additional
            datasets can be added later using the ``add_data`` method on
            the viewer object.
        x_attr : str or `~glue.core.component_id.ComponentID`, optional
            The attribute to show on the x axis. This should be a pixel or
            world coordinate `~glue.core.component_id.ComponentID`.
        widget : {'bqplot', 'matplotlib'}
            Whether to use bqplot or Matplotlib as the front-end.
        show : bool, optional
            Whether to show the view immediately (`True`) or whether to only
            show it later if the ``show()`` method is called explicitly
            (`False`).
        """
        if widget == 'bqplot':
            viewer_cls = BqplotProfileView
        elif widget == 'matplotlib':
            viewer_cls = ProfileJupyterViewer
        else:
            raise ValueError("Widget type should be 'matplotlib'")

        data = validate_data_argument(self.data_collection, data)

        new_viewer_message = NewViewerMessage(viewer_cls, data=data, x_attr=x_attr)

        hub.broadcast(new_viewer_message)

        # view = self.new_data_viewer(viewer_cls, data=data, show=show)
        #
        # if x is not None:
        #     x = data.id[x]
        #     view.state.x_att = x
        #
        # return view
