from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView

from jdaviz.core.registries import viewer_registry

from .events import CreateCubeViewerMessage, ChangeSliderMessage


@viewer_registry("g-cubeviz-image-viewer")
class CubeVizImageView(BqplotImageView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.session.hub.subscribe(self, ChangeSliderMessage,
                                   handler=self._on_slider_changed)

        # Broadcast a new event indicating that this viewer has been created
        #  in order for the slice slider to know the bounds of the data.
        create_cube_viewer_message = CreateCubeViewerMessage(self, sender=self)
        self.session.hub.broadcast(create_cube_viewer_message)

    def _on_slider_changed(self, msg):
        self.state.slices = (msg.value, 0, 0)
