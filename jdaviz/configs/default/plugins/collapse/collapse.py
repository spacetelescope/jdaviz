from astropy import units as u
from astropy import units as u
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from glue.core.coordinates import WCSCoordinates
from glue.core import Data, Subset
from specutils import Spectrum1D
from spectral_cube import SpectralCube
from traitlets import Bool, List, Unicode, Int, observe

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['Collapse']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tool_registry('g-collapse')
class Collapse(TemplateMixin):
    template = load_template("collapse.vue", __file__).tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    data_items = List([]).tag(sync=True)
    selected_data_item = Unicode().tag(sync=True)
    axes = List([]).tag(sync=True)
    selected_axis = Int(0).tag(sync=True)
    funcs = List(['Mean', 'Median', 'Min', 'Max']).tag(sync=True)
    selected_func = Unicode('Mean').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None

    def _on_data_updated(self, msg):
        self.data_items = [x.label for x in self.data_collection]

    @observe('selected_data_item')
    def _on_data_item_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event['new']))

        self.axes = list(range(len(self._selected_data.shape)))

    def vue_collapse(self, *args, **kwargs):
        spec = self._selected_data.get_object(cls=SpectralCube)

        collapsed_spec = getattr(spec, self.selected_func.lower())(
            axis=self.selected_axis)

        data = Data(coords=collapsed_spec.wcs)
        data['flux'] = collapsed_spec.filled_data[...]
        data.get_component('flux').units = str(collapsed_spec.unit)
        data.meta.update(collapsed_spec.meta)

        self.data_collection[f"Collapsed {self._selected_data.label}"] = data

        self.dialog = False
