import numpy as np
from astropy import units as u
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue.core.subset import Subset
from photutils.aperture import aperture_photometry
from traitlets import Bool, Float, List

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import (NewViewerMessage, RemoveViewerMessage,
                                AddDataMessage, RemoveDataMessage)
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin):
    template = load_template("aper_phot_simple.vue", __file__).tag(sync=True)
    # viewer_items = List(['imviz-0']).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    background_value = Float(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Does not work! Should we just confine this plugin to default viewer?
        # self.hub.subscribe(self, NewViewerMessage, handler=self._on_viewer_changed)
        # self.hub.subscribe(self, RemoveViewerMessage, handler=self._on_viewer_changed)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        # self._selected_viewer_id = self.viewer_items[0]  # Start with default viewer
        self._selected_viewer_id = 'imviz-0'
        self._selected_data = None
        self._selected_subset = None

    # def _on_viewer_changed(self):
    #    self.viewer_items = self.app.get_viewer_ids(prefix='imviz')
    #
    #    if self._selected_viewer_id not in self.viewer_items:
    #        self._selected_viewer_id = self.viewer_items[0]  # Should always have imviz-0
    #        self._on_viewer_data_changed()

    def _on_viewer_data_changed(self, msg=None):
        self.result_available = False
        self.results = []

        # NOTE: Unlike other plugins, this does not check viewer ID because
        # Imviz allows photometry from any number of open image viewers.
        viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
        self.dc_items = [lyr.layer.label for lyr in viewer.state.layers
                         if layer_is_image_data(lyr.layer)]
        self.subset_items = [lyr.layer.label for lyr in viewer.state.layers
                             if (lyr.layer.label.startswith('Subset') and
                                 isinstance(lyr.layer, Subset) and lyr.layer.ndim == 2)]

    # def vue_viewer_selected(self, event):
    #    self._selected_viewer_id = event

    def vue_data_selected(self, event):
        self._selected_data = self.app.data_collection[self.app.data_collection.index(event)]

    def vue_subset_selected(self, event):
        self._selected_subset = None
        subset = None
        viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
        for lyr in viewer.state.layers:
            if lyr.layer.label == event:
                subset = lyr.layer
                break
        if subset is None:
            return
        self._selected_subset = subset.data.get_selection_definition(subset_id=event, format='astropy-regions')

    def vue_do_aper_phot(self, *args, **kwargs):
        if self._selected_data is None or self._selected_subset is None:
            self.result_available = False
            self.results = []  # list of {'function': str, 'result': str}

        data = self._selected_data
        comp = data.get_component(data.main_components[0])
        comp_no_bg = comp.data - self.background_value
        if comp.units is not None:
            img = comp_no_bg << u.Unit(comp.units)
        else:
            img = comp_no_bg
        mask = np.isnan(img)
        result = aperture_photometry(img, self._selected_subset, error=None, mask=mask,
                                     method='exact', subpixels=5, wcs=data.coords)

        tmp = []
        for colname in result.colnames:
            if colname == 'id':
                continue
            tmp.append({'function': colname, 'result': str(result[colname][0])})

        # TODO: Patrick also wants some extra stats...

        self.results = tmp
        self.result_available = True

        # TODO: Append instead of overwrite?
        # Attach to app for Python extraction.
        self.app._aper_phot_results = result
