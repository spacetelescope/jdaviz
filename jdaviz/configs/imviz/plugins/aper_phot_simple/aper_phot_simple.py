from datetime import datetime

import numpy as np
from astropy import units as u
from astropy.table import QTable
from astropy.time import Time
from bqplot import pyplot as bqplt
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from ipywidgets import widget_serialization
from regions.shapes.rectangle import RectanglePixelRegion
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin):
    template_file = __file__, "aper_phot_simple.vue"
    dc_items = List([]).tag(sync=True)
    data_selected = Unicode("").tag(sync=True)
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("").tag(sync=True)
    bg_subset_items = List(['Manual']).tag(sync=True)
    bg_subset_selected = Unicode("Manual").tag(sync=True)
    background_value = Any(0).tag(sync=True)
    pixel_area = Any(0).tag(sync=True)
    counts_factor = Any(0).tag(sync=True)
    flux_scaling = Any(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)
    plot_types = List([]).tag(sync=True)
    current_plot_type = Unicode().tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    radial_plot = Any('').tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, AddDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, RemoveDataMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetCreateMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetDeleteMessage, handler=self._on_viewer_data_changed)
        self.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_viewer_data_changed)

        self._selected_data = None
        self._selected_subset = None
        self.plot_types = ["Radial Profile", "Radial Profile (Raw)"]
        self.current_plot_type = self.plot_types[0]

    def reset_results(self):
        self.result_available = False
        self.results = []
        self.plot_available = False
        self.radial_plot = ''
        bqplt.clear()

    def _on_viewer_data_changed(self, msg=None):
        # To support multiple viewers, we allow the entire data collection.
        self.dc_items = [lyr.label for lyr in self.app.data_collection
                         if layer_is_image_data(lyr)]

        self.subset_items = [lyr.label for lyr in self.app.data_collection.subset_groups
                             if lyr.label.startswith('Subset')]
        self.bg_subset_items = ['Manual'] + self.subset_items

    @observe('data_selected')
    def _data_selected_changed(self, event={}):
        data_selected = event.get('new', self.data_selected)
        try:
            self._selected_data = self.app.data_collection[
                self.app.data_collection.labels.index(data_selected)]
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
            self.reset_results()
            self._selected_data = None
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {data_selected}: {repr(e)}", color='error', sender=self))

        # Auto-populate background, if applicable
        self._bg_subset_selected_changed()

    def _get_region_from_subset(self, subset):
        for subset_grp in self.app.data_collection.subset_groups:
            if subset_grp.label == subset:
                for sbst in subset_grp.subsets:
                    if sbst.data.label == self.data_selected:
                        # TODO: https://github.com/glue-viz/glue-astronomy/issues/52
                        return sbst.data.get_selection_definition(
                                subset_id=subset, format='astropy-regions')
        else:
            raise ValueError(f'Subset "{subset}" not found')

    @observe('subset_selected')
    def _subset_selected_changed(self, event={}):
        subset_selected = event.get('new', self.subset_selected)
        if self._selected_data is None:
            self.reset_results()
            return

        try:
            self._selected_subset = self._get_region_from_subset(subset_selected)
            self._selected_subset.meta['label'] = subset_selected
        except Exception as e:
            self._selected_subset = None
            self.reset_results()
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {subset_selected}: {repr(e)}", color='error', sender=self))

    @observe('bg_subset_selected')
    def _bg_subset_selected_changed(self, event={}):
        bg_subset_selected = event.get('new', self.bg_subset_selected)
        if bg_subset_selected == 'Manual':
            # we'll later access the user's self.background_value directly
            return

        try:
            # Basically same way image stats are calculated in vue_do_aper_phot()
            # except here we only care about one stat for the background.
            data = self._selected_data
            reg = self._get_region_from_subset(bg_subset_selected)
            comp = data.get_component(data.main_components[0])
            aper_mask_stat = reg.to_mask(mode='center')
            img_stat = aper_mask_stat.get_values(comp.data, mask=None)

            # photutils/background/_utils.py --> nanmedian()
            self.background_value = np.nanmedian(img_stat)  # Naturally in data unit

        except Exception as e:
            self.background_value = 0
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {bg_subset_selected}: {repr(e)}", color='error', sender=self))

    def vue_do_aper_phot(self, *args, **kwargs):
        if self._selected_data is None or self._selected_subset is None:
            self.reset_results()
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
            comp_no_bg_cutout = aper_mask_stat.cutout(comp_no_bg)
            img_stat = aper_mask_stat.get_values(comp_no_bg, mask=None)
            include_pixarea_fac = False
            include_counts_fac = False
            include_flux_scale = False
            if comp.units:
                img_unit = u.Unit(comp.units)
                img = img * img_unit
                img_stat = img_stat * img_unit
                bg = bg * img_unit
                comp_no_bg_cutout = comp_no_bg_cutout * img_unit
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

            # Radial profile (Raw)
            reg_bb = reg.bounding_box
            reg_ogrid = np.ogrid[reg_bb.iymin:reg_bb.iymax, reg_bb.ixmin:reg_bb.ixmax]
            radial_dx = reg_ogrid[1] - reg.center.x
            radial_dy = reg_ogrid[0] - reg.center.y
            radial_r = np.hypot(radial_dx, radial_dy).ravel()  # pix
            radial_img = comp_no_bg_cutout.ravel()

            if comp.units:
                y_data = radial_img.value
                y_label = radial_img.unit.to_string()
            else:
                y_data = radial_img
                y_label = 'Value'

            # Radial profile
            if self.current_plot_type == "Radial Profile":
                # This algorithm is from the imexam package,
                # see licenses/IMEXAM_LICENSE.txt for more details
                radial_r = list(radial_r)
                y_data = np.bincount(radial_r, y_data) / np.bincount(radial_r)
                radial_r = np.arange(len(y_data))
                markerstyle = 'g--o'
            else:
                markerstyle = 'go'

            bqplt.clear()
            # NOTE: default margin in bqplot is 60 in all directions
            fig = bqplt.figure(1, title='Radial profile from Subset center',
                               fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                               title_style={'font-size': '12px'})  # TODO: Jenn wants title at bottom. # noqa
            bqplt.plot(radial_r, y_data, markerstyle, figure=fig, default_size=1)
            bqplt.xlabel(label='pix', mark=fig.marks[-1], figure=fig)
            bqplt.ylabel(label=y_label, mark=fig.marks[-1], figure=fig)

        except Exception as e:  # pragma: no cover
            self.reset_results()
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
                        key not in ('xcenter', 'ycenter', 'sky_center', 'npix',
                                    'aperture_sum_counts')):
                    x = f'{x:.4e}'
                    tmp.append({'function': key, 'result': x})
                elif key == 'sky_center' and x is not None:
                    tmp.append({'function': 'RA center', 'result': f'{x.ra.deg:.4f} deg'})
                    tmp.append({'function': 'Dec center', 'result': f'{x.dec.deg:.4f} deg'})
                elif key in ('xcenter', 'ycenter', 'npix'):
                    x = f'{x:.1f}'
                    tmp.append({'function': key, 'result': x})
                elif key == 'aperture_sum_counts' and x is not None:
                    x = f'{x:.4e} ({d["aperture_sum_counts_err"]:.4e})'
                    tmp.append({'function': key, 'result': x})
                elif not isinstance(x, str):
                    x = str(x)
                    tmp.append({'function': key, 'result': x})
            self.results = tmp
            self.result_available = True
            self.radial_plot = fig
            self.bqplot_figs_resize = [fig]
            self.plot_available = True


def _qtable_from_dict(d):
    # TODO: Is there more elegant way to do this?
    tmp = {}
    for key, x in d.items():
        tmp[key] = [x]
    return QTable(tmp)
