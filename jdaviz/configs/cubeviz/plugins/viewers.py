from glue_jupyter.bqplot.profile import BqplotProfileView
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewers
from glue.core.message import DataCollectionMessage


class CubeVizDataImShow(BqplotImageView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_hub(self, hub):
        self.hub = hub
        self.hub.subscribe(self, DataCollectionMessage, self._on_data_added)

    def _on_data_added(self, msg):
        try:
            self.add_data(msg.sender[0])
        except:
            pass


class CubeVizErrorImShow(BqplotImageView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_hub(self, hub):
        self.hub = hub
        self.hub.subscribe(self, DataCollectionMessage, self._on_data_added)

    def _on_data_added(self, msg):
        try:
            self.add_data(msg.sender[1])
        except:
            pass


class CubeVizDQImShow(BqplotImageView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_hub(self, hub):
        self.hub = hub
        self.hub.subscribe(self, DataCollectionMessage, self._on_data_added)

    def _on_data_added(self, msg):
        try:
            self.add_data(msg.sender[2])
        except:
            pass


class CubeVizProfileView(BqplotProfileView):

    def setup_hub(self, hub):
        self.hub = hub
        self.hub.subscribe(self, DataCollectionMessage, self._on_data_added)

    def _on_data_added(self, msg):
        try:
            self.add_data(msg.sender[1])
        except:
            pass


viewers.add("cv-profile-1d", label="Profile 1D", cls=CubeVizProfileView)
viewers.add("cv-data-imshow", label="Image 2D", cls=CubeVizDataImShow)
viewers.add("cv-error-imshow", label="Image 2D", cls=CubeVizErrorImShow)
viewers.add("cv-dq-imshow", label="Image 2D", cls=CubeVizDQImShow)
