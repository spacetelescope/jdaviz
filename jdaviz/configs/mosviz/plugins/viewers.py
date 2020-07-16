from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from specutils import Spectrum1D
from glue_jupyter.table import TableViewer
import ipyvuetify as v
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from traitlets import Unicode, List, Bool, observe
from astropy.table import QTable
from glue.core.message import SubsetCreateMessage, SubsetUpdateMessage, DataCollectionAddMessage
from glue.core import HubListener
from glue.core.state_objects import State
from glue_jupyter.state_traitlets_helpers import GlueState
from echo import CallbackProperty, DictCallbackProperty, ListCallbackProperty
import astropy.units as u
import numpy as np

from jdaviz.core.registries import viewer_registry

__all__ = ['MOSVizProfileView', 'MOSVizImageView']


@viewer_registry("mosviz-profile-viewer", label="Profile 1D (MOSViz)")
class MOSVizProfileView(BqplotProfileView):
    default_class = Spectrum1D

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]


@viewer_registry("mosviz-image-viewer", label="Image 2D (MOSViz)")
class MOSVizImageView(BqplotImageView):

    default_class = None

    def data(self, cls=None):
        return [layer_state.layer #.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]


DEFAULT_COLUMNS = ['ID', 'Image', '1D Spectrum', '2D Spectrum', 'RA', 'DEC']


@viewer_registry("mosviz-table-viewer", label="Table (MOSViz)")
class MOSVizTableViewer(TableViewer):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)


class TableState(State):
    headers = ListCallbackProperty([])
    selected_row = ListCallbackProperty([])
    items = ListCallbackProperty([])
    dc_items = ListCallbackProperty([])
    comp_items = ListCallbackProperty([])
    selected_dc_item = CallbackProperty()


class NewTableViewer(v.VuetifyTemplate, HubListener):
    template = load_template("table_viewer.vue", __file__).tag(sync=True)
    state = GlueState().tag(sync=True)

    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = session

        self.state = TableState()

        self._table = QTable()

        # self._session.hub.subscribe(
        #     self, SubsetCreateMessage,
        #     handler=self._on_subset_updated)
        #
        # self._session.hub.subscribe(
        #     self, SubsetUpdateMessage,
        #     handler=self._on_subset_updated)
        #
        # self._session.hub.subscribe(
        #     self, DataCollectionAddMessage,
        #     handler=self._on_data_collection_changed)
        #
        # self._on_data_collection_changed()

    def _update_headers(self):
        self.state.headers = [{
            'text': x,
            'align': 'start',
            'sortable': False,
            'value': x,
          } for x in self._table.colnames]

    def _update_items(self):
        self.state.items = [{
            k: v.to_string() if hasattr(v, 'unit') else v
            for k, v in zip(self._table[i].colnames, self._table[i])}
            for i in range(len(self._table))]

    def _parse_data(self, data):
        for c in data.components:
            comp = data.get_component(c)
            self._table[c.label] = u.Quantity(comp.data, comp.units) \
                if type(comp.data) is np.ndarray else np.array(comp.data)

        self._update_headers()
        self._update_items()

    def _create_table(self, comp_data, label):
        data = Data(label="MOS Table")
        data.add_component(comp_data, label=label)
        self.app.data_collection.append(data)

        viewer_cls = viewer_registry.members["mosviz-table-viewer"]['cls']

        new_viewer_message = NewViewerMessage(
            viewer_cls, data=data, sender=self)

        self.app.hub.broadcast(new_viewer_message)