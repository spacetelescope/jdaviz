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
    pixel_scale = Any(0).tag(sync=True)
    counts_factor = Any(0).tag(sync=True)
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
            self.counts_factor = 0
            self.pixel_scale = 0

            # Extract telescope specific unit conversion factors, if applicable.
            meta = self._selected_data.meta
            telescope = meta.get('TELESCOP', '').lower()
            comp = self._selected_data.get_component(self._selected_data.main_components[0])
            if telescope == 'jwst':
                if 'PIXAR_A2' in meta:
                    self.pixel_scale = meta['PIXAR_A2']
                if (comp.units and u.sr in comp.units.bases and 'photometry' in meta and
                        'conversion_megajanskys' in meta['photometry']):
                    self.counts_factor = meta['photometry']['conversion_megajanskys']
            elif telescope == 'hst':
                # TODO: Add more HST support, as needed.
                # HST pixel scales are from instrument handbooks.
                # This is really not used because HST data does not have sr in unit.
                # This is only for completeness.
                # For counts conversion, PHOTFLAM is used to convert "counts" to flux manually,
                # which is the opposite of JWST, so we just do not do it here.
                instrument = meta.get('INSTRUME', '').lower()
                detector = meta.get('DETECTOR', '').lower()
                if instrument == 'acs':
                    if detector == 'wfc':
                        self.pixel_scale = 0.05 * 0.05
                    elif detector == 'hrc':
                        self.pixel_scale = 0.028 * 0.025
                    elif detector == 'sbc':
                        self.pixel_scale = 0.034 * 0.03
                elif instrument == 'wfc3' and detector == 'uvis':
                    self.pixel_scale = 0.04 * 0.04

        except Exception as e:
            self._selected_data = None
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {event}: {repr(e)}", color='error', sender=self))

    def vue_subset_selected(self, event):
        subset = None
        try:
            viewer = self.app.get_viewer_by_id(self._selected_viewer_id)
            for lyr in viewer.layers:
                if lyr.layer.label == event and lyr.layer.data.label == self._selected_data.label:
                    subset = lyr.layer
                    break

            # TODO: https://github.com/glue-viz/glue-astronomy/issues/52
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
            npix = np.sum(aper_mask) * u.pix
            img = aper_mask.get_values(comp_no_bg, mask=None)
            aper_mask_stat = reg.to_mask(mode='center')
            img_stat = aper_mask_stat.get_values(comp_no_bg, mask=None)
            pixscale_fac = 1.0
            include_pixscale_fac = False
            include_counts_fac = False
            if comp.units:
                img_unit = u.Unit(comp.units)
                img = img * img_unit
                img_stat = img_stat * img_unit
                bg = bg * img_unit
                if u.sr in img_unit.bases:  # TODO: Better way to do this?
                    pixscale = float(self.pixel_scale) * (u.arcsec * u.arcsec / u.pix)
                    if not np.allclose(pixscale, 0):
                        pixscale_fac = npix * pixscale.to(u.sr / u.pix)
                        include_pixscale_fac = True
                if img_unit != u.count:
                    ctfac = float(self.counts_factor)
                    if not np.allclose(ctfac, 0):
                        include_counts_fac = True
            apersum = np.nansum(img) * pixscale_fac
            d = {'id': 1,
                 'xcenter': reg.center.x * u.pix,
                 'ycenter': reg.center.y * u.pix}
            if data.coords is not None:
                d['sky_center'] = data.coords.pixel_to_world(reg.center.x, reg.center.y)
            else:
                d['sky_center'] = None
            d.update({'background': bg,
                      'npix': npix,
                      'aperture_sum': apersum})
            if include_counts_fac:
                counts_fac = ctfac * (apersum.unit / (u.count / u.s))
                d.update({'aperture_sum_counts': apersum / counts_fac,
                          'counts_fac': counts_fac})
            else:
                d.update({'aperture_sum_counts': None,
                          'counts_fac': None})
            if include_pixscale_fac:
                d['pixscale_fac'] = pixscale_fac
            else:
                d['pixscale_fac'] = None

            # Extra stats beyond photutils.
            d.update({'mean': np.nanmean(img_stat),
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
                if key in ('id', 'data_label', 'subset_label', 'background', 'pixscale_fac',
                           'counts_fac'):
                    continue
                if (isinstance(x, (int, float, u.Quantity)) and
                        key not in ('xcenter', 'ycenter', 'npix')):
                    x = f'{x:.4e}'
                elif key == 'npix':
                    x = f'{x:.1f}'
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
