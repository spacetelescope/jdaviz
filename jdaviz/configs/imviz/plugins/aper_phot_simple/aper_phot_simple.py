from datetime import datetime

import numpy as np
from astropy import units as u
from astropy.table import QTable
from astropy.time import Time
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from glue.core.subset import Subset
from regions.shapes.rectangle import RectanglePixelRegion
from traitlets import Any, Bool, List

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin):
    template_file = __file__, "aper_phot_simple.vue"
    dc_items = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    background_value = Any(0).tag(sync=True)
    pixel_area = Any(0).tag(sync=True)
    counts_factor = Any(0).tag(sync=True)
    flux_scaling = Any(0).tag(sync=True)
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
            self.pixel_area = 0
            self.flux_scaling = 0

            # Extract telescope specific unit conversion factors, if applicable.
            meta = self._selected_data.meta
            if 'telescope' in meta:
                telescope = meta['telescope']
            else:
                telescope = meta.get('TELESCOP', '')
            if telescope == 'JWST':
                if 'photometry' in meta and 'pixelarea_arcsecsq' in meta['photometry']:
                    self.pixel_area = meta['photometry']['pixelarea_arcsecsq']
            elif telescope == 'HST':
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
                        self.pixel_area = 0.05 * 0.05
                    elif detector == 'hrc':  # pragma: no cover
                        self.pixel_area = 0.028 * 0.025
                    elif detector == 'sbc':  # pragma: no cover
                        self.pixel_area = 0.034 * 0.03
                elif instrument == 'wfc3' and detector == 'uvis':  # pragma: no cover
                    self.pixel_area = 0.04 * 0.04

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
            try:
                bg = float(self.background_value)
            except ValueError:  # Clearer error message
                raise ValueError('Missing or invalid background value')
            comp_no_bg = comp.data - bg

            # TODO: Use photutils when it supports astropy regions.
            if not isinstance(reg, RectanglePixelRegion):
                aper_mask = reg.to_mask(mode='exact')
            else:
                # TODO: https://github.com/astropy/regions/issues/404 (moot if we use photutils?)
                aper_mask = reg.to_mask(mode='subpixels', subpixels=32)
            npix = np.sum(aper_mask) * u.pix
            img = aper_mask.get_values(comp_no_bg, mask=None)
            aper_mask_stat = reg.to_mask(mode='center')
            img_stat = aper_mask_stat.get_values(comp_no_bg, mask=None)
            include_pixarea_fac = False
            include_counts_fac = False
            include_flux_scale = False
            if comp.units:
                img_unit = u.Unit(comp.units)
                img = img * img_unit
                img_stat = img_stat * img_unit
                bg = bg * img_unit
                if u.sr in img_unit.bases:  # TODO: Better way to detect surface brightness unit?
                    try:
                        pixarea = float(self.pixel_area)
                    except ValueError:  # Clearer error message
                        raise ValueError('Missing or invalid pixel area')
                    if not np.allclose(pixarea, 0):
                        include_pixarea_fac = True
                if img_unit != u.count:
                    try:
                        ctfac = float(self.counts_factor)
                    except ValueError:  # Clearer error message
                        raise ValueError('Missing or invalid counts conversion factor')
                    if not np.allclose(ctfac, 0):
                        include_counts_fac = True
                try:
                    flux_scale = float(self.flux_scaling)
                except ValueError:  # Clearer error message
                    raise ValueError('Missing or invalid flux scaling')
                if not np.allclose(flux_scale, 0):
                    include_flux_scale = True
            rawsum = np.nansum(img)
            d = {'id': 1,
                 'xcenter': reg.center.x * u.pix,
                 'ycenter': reg.center.y * u.pix}
            if data.coords is not None:
                d['sky_center'] = data.coords.pixel_to_world(reg.center.x, reg.center.y)
            else:
                d['sky_center'] = None
            d.update({'background': bg,
                      'npix': npix})
            if include_pixarea_fac:
                pixarea = pixarea * (u.arcsec * u.arcsec / u.pix)
                pixarea_fac = npix * pixarea.to(u.sr / u.pix)
                d.update({'aperture_sum': rawsum * pixarea_fac,
                          'pixarea_tot': pixarea_fac})
            else:
                d.update({'aperture_sum': rawsum,
                          'pixarea_tot': None})
            if include_counts_fac:
                ctfac = ctfac * (rawsum.unit / u.count)
                sum_ct = rawsum / ctfac
                d.update({'aperture_sum_counts': sum_ct,
                          'aperture_sum_counts_err': np.sqrt(sum_ct.value) * sum_ct.unit,
                          'counts_fac': ctfac})
            else:
                d.update({'aperture_sum_counts': None,
                          'aperture_sum_counts_err': None,
                          'counts_fac': None})
            if include_flux_scale:
                flux_scale = flux_scale * rawsum.unit
                d.update({'aperture_sum_mag': -2.5 * np.log10(rawsum / flux_scale) * u.mag,
                          'flux_scaling': flux_scale})
            else:
                d.update({'aperture_sum_mag': None,
                          'flux_scaling': None})

            # Extra stats beyond photutils.
            d.update({'mean': np.nanmean(img_stat),
                      'stddev': np.nanstd(img_stat),
                      'median': np.nanmedian(img_stat),
                      'min': np.nanmin(img_stat),
                      'max': np.nanmax(img_stat),
                      'data_label': data.label,
                      'subset_label': reg.meta.get('label', ''),
                      'timestamp': Time(datetime.utcnow())})

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

        except Exception as e:  # pragma: no cover
            self.result_available = False
            self.results = []
            self.hub.broadcast(SnackbarMessage(
                f"Aperture photometry failed: {repr(e)}", color='error', sender=self))

        else:
            # Parse results for GUI.
            tmp = []
            for key, x in d.items():
                if key in ('id', 'data_label', 'subset_label', 'background', 'pixarea_tot',
                           'counts_fac', 'aperture_sum_counts_err', 'flux_scaling', 'timestamp'):
                    continue
                if (isinstance(x, (int, float, u.Quantity)) and
                        key not in ('xcenter', 'ycenter', 'npix', 'aperture_sum_counts')):
                    x = f'{x:.4e}'
                elif key == 'npix':
                    x = f'{x:.1f}'
                elif key == 'aperture_sum_counts' and x is not None:
                    x = f'{x:.4e} ({d["aperture_sum_counts_err"]:.4e})'
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
