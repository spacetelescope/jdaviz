import numpy as np
from astropy import units as u
from astropy.table import QTable
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue.core.subset import Subset
from traitlets import Any, Bool, List

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin):
    template = load_template("aper_phot_simple.vue", __file__).tag(sync=True)
    dc_items = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    background_value = Any(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetCreateMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetDeleteMessage,
                           handler=lambda x: self._on_viewer_data_changed())
        self.hub.subscribe(self, SubsetUpdateMessage,
                           handler=lambda x: self._on_viewer_data_changed())

        # TODO: Allow switching viewer in the future. Need new "messages" to subscribe
        #       to in viewer create/destroy events.
        self._selected_viewer_id = 'imviz-0'

        self._selected_data = None
        self._selected_subset = None

    def _on_viewer_data_changed(self, msg=None):
        # NOTE: Unlike other plugins, this does not check viewer ID because
        # Imviz allows photometry from any number of open image viewers.
        viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
        self.dc_items = [lyr.layer.label for lyr in viewer.state.layers
                         if layer_is_image_data(lyr.layer)]
        self.subset_items = [lyr.layer.label for lyr in viewer.state.layers
                             if (lyr.layer.label.startswith('Subset') and
                                 isinstance(lyr.layer, Subset) and lyr.layer.ndim == 2)]

    def vue_data_selected(self, event):
        try:
            self._selected_data = self.app.data_collection[
                self.app.data_collection.labels.index(event)]
        except Exception as e:
            self._selected_data = None
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {event}: {repr(e)}", color='error', sender=self))

    def vue_subset_selected(self, event):
        subset = None
        viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
        for lyr in viewer.state.layers:
            if lyr.layer.label == event:
                subset = lyr.layer
                break
        try:
            self._selected_subset = subset.data.get_selection_definition(
                subset_id=event, format='astropy-regions')
            self._selected_subset.meta['label'] = subset.label
        except Exception as e:
            self._selected_subset = None
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {event}: {repr(e)}", color='error', sender=self))

    def vue_do_aper_phot(self, *args, **kwargs):
        if self._selected_data is None or self._selected_subset is None:
            self.result_available = False
            self.results = []
            self.hub.broadcast(SnackbarMessage(
                "No data for aperture photometry", color='error', sender=self))
            return

        data = self._selected_data
        reg = self._selected_subset

        try:
            comp = data.get_component(data.main_components[0])
            bg = float(self.background_value)
            comp_no_bg = comp.data - bg

            # TODO: Use photutils when it supports astropy regions.
            aper_mask = reg.to_mask(mode='exact')
            img = aper_mask.get_values(comp_no_bg, mask=None)
            aper_mask_stat = reg.to_mask(mode='center')
            img_stat = aper_mask_stat.get_values(comp_no_bg, mask=None)
            if comp.units:
                img_unit = u.Unit(comp.units)
                img = img * img_unit
                img_stat = img_stat * img_unit
                bg = bg * img_unit
            d = {'id': 1,
                 'xcenter': reg.center.x * u.pix,
                 'ycenter': reg.center.y * u.pix,
                 'aperture_sum': np.nansum(img)}
            if data.coords is not None:
                d['sky_center'] = data.coords.pixel_to_world(reg.center.x, reg.center.y)
            else:
                d['sky_center'] = None

            # Extra stats beyond photutils.
            d.update({'background': bg,
                      'mean': np.nanmean(img_stat),
                      'stddev': np.nanstd(img_stat),
                      'median': np.nanmedian(img_stat),
                      'min': np.nanmin(img_stat),
                      'max': np.nanmax(img_stat),
                      'data_label': data.label,
                      'subset_label': reg.meta.get('label', '')})

            # Attach to app for Python extraction.
            if (not hasattr(self.app, '_aper_phot_results') or
                    not isinstance(self.app._aper_phot_results, QTable)):
                self.app._aper_phot_results = _qtable_from_dict(d)
            else:
                try:
                    d['id'] = self.app._aper_phot_results['id'].max() + 1
                    self.app._aper_phot_results.add_row(d.values())
                except Exception:  # Discard incompatible QTable
                    d['id'] = 1
                    self.app._aper_phot_results = _qtable_from_dict(d)

        except Exception as e:
            self.result_available = False
            self.results = []
            self.hub.broadcast(SnackbarMessage(
                f"Aperture photometry failed: {repr(e)}", color='error', sender=self))

        else:
            # Parse results for GUI.
            tmp = []
            for key, x in d.items():
                if key in ('id', 'data_label', 'subset_label', 'background'):
                    continue
                if isinstance(x, (int, float, u.Quantity)) and key not in ('xcenter', 'ycenter'):
                    x = f'{x:.4e}'
                elif not isinstance(x, str):
                    x = str(x)
                tmp.append({'function': key, 'result': x})
            self.results = tmp
            self.result_available = True


def _qtable_from_dict(d):
    # TODO: Is there more elegant way to do this?
    tmp = {}
    for key, x in d.items():
        tmp[key] = [x]
    return QTable(tmp)
