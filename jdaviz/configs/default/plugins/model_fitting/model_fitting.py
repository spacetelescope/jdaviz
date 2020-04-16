from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from traitlets import Bool, List

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from .fitting_backend import fit_model_to_spectrum

__all__ = ['ModelFitting']


@tray_registry('g-model-fitting')
class ModelFitting(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("model_fitting.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    # Hard coding this for now, but will want to pull from a config file
    available_models = List(["Gaussian1D", "Const1D"]).tag(sync=True)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=self._on_data_updated)

        self._selected_data = None

    def _on_data_updated(self, msg):
        self.dc_items = [x.label for x in self.data_collection]

    def vue_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event))

    def vue_model_fitting(self, *args, **kwargs):
        # This will be where the model fitting code is run
        self.dialog = False
