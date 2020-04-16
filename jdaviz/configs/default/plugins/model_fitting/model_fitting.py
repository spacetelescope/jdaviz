from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)
from traitlets import Bool, List, Dict, Unicode

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

from .fitting_backend import fit_model_to_spectrum

__all__ = ['ModelFitting']

def initialize_gaussian1d():
    pass

def initialize_const1d():
    pass

model_initializers = {"Gaussian1D": initialize_gaussian1d,
                      "Const1D": initialize_const1d}

model_parameters = {"Gaussian1D": [],
                    "Const1D": []}

@tray_registry('g-model-fitting')
class ModelFitting(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("model_fitting.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    temp_name = Unicode().tag(sync=True)
    # Hard coding this for now, but will want to pull from a config file
    available_models = List(["Gaussian1D", "Const1D"]).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                          handler=self._on_data_updated)

        self._selected_data = None
        self._selected_models = Dict({}).tag(sync=True)

    def _on_data_updated(self, msg):
       self.dc_items = [x.label for x in self.data_collection]

    def vue_data_selected(self, event):
        self._selected_data = next((x for x in self.data_collection
                                    if x.label == event))

    def vue_model_selected(self, event):
        # Add the model selected to the list of models
        #self._selected_models[event.name] = {"model_type" = event.model}
        pass

    def vue_add_model(self, event):
        # Add the selected model and input string ID to the list of models
        pass

    def vue_model_fitting(self, *args, **kwargs):
        # This will be where the model fitting code is run
        self.dialog = False
