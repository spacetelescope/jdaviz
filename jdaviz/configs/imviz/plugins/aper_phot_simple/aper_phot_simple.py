from datetime import datetime

import numpy as np
from astropy import units as u
from astropy.table import QTable
from astropy.time import Time
from bqplot import pyplot as bqplt
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage, SubsetUpdateMessage
from ipywidgets import widget_serialization
from photutils.aperture import ApertureStats
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.configs.imviz.helper import layer_is_image_data
from jdaviz.core.events import AddDataMessage, RemoveDataMessage, SnackbarMessage
from jdaviz.core.region_translators import regions2aperture
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, SubsetSelect

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

        self.subset = SubsetSelect(self,
                                   'subset_items',
                                   'subset_selected',
                                   default_text=None,
                                   allowed_type='spatial')

        self.bg_subset = SubsetSelect(self,
                                      'bg_subset_items',
                                      'bg_subset_selected',
                                      default_text='Manual',
                                      allowed_type='spatial')

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

        # update self._selected_subset with the new self._selected_data
        self._subset_selected_changed()

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
        if self._selected_data is None or subset_selected == '':
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
            aperture = regions2aperture(reg)
            include_pixarea_fac = False
            include_counts_fac = False
            include_flux_scale = False
            comp_data = comp.data
            if comp.units:
                img_unit = u.Unit(comp.units)
                bg = bg * img_unit
                comp_data = comp_data << img_unit

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
            phot_aperstats = ApertureStats(comp_data, aperture, wcs=data.coords, local_bkg=bg)
            phot_table = phot_aperstats.to_table(columns=(
                'id', 'xcentroid', 'ycentroid', 'sky_centroid', 'sum', 'sum_aper_area',
                'min', 'max', 'mean', 'median', 'mode', 'std', 'mad_std', 'var',
                'biweight_location', 'biweight_midvariance', 'fwhm', 'semimajor_sigma',
                'semiminor_sigma', 'orientation', 'eccentricity'))  # Some cols excluded, add back as needed.  # noqa
            phot_table['xcentroid'].unit = u.pix  # photutils only assumes, we make it real
            phot_table['ycentroid'].unit = u.pix
            rawsum = phot_table['sum'][0]
            npix = phot_table['sum_aper_area'][0]

            if include_pixarea_fac:
                pixarea = pixarea * (u.arcsec * u.arcsec / (u.pix * u.pix))
                pixarea_fac = npix * pixarea.to(u.sr / (u.pix * u.pix))
                phot_table['sum'] = [rawsum * pixarea_fac]
            else:
                pixarea_fac = None

            if include_counts_fac:
                ctfac = ctfac * (rawsum.unit / u.count)
                sum_ct = rawsum / ctfac
                sum_ct_err = np.sqrt(sum_ct.value) * sum_ct.unit
            else:
                ctfac = None
                sum_ct = None
                sum_ct_err = None

            if include_flux_scale:
                flux_scale = flux_scale * rawsum.unit
                sum_mag = -2.5 * np.log10(rawsum / flux_scale) * u.mag
            else:
                flux_scale = None
                sum_mag = None

            # Extra info beyond photutils.
            phot_table.add_columns(
                [bg, pixarea_fac, sum_ct, sum_ct_err, ctfac, sum_mag, flux_scale, data.label,
                 reg.meta.get('label', ''), Time(datetime.utcnow())],
                names=['background', 'pixarea_tot', 'aperture_sum_counts',
                       'aperture_sum_counts_err', 'counts_fac', 'aperture_sum_mag', 'flux_scaling',
                       'data_label', 'subset_label', 'timestamp'],
                indexes=[4, 6, 6, 6, 6, 6, 6, 21, 21, 21])

            # Attach to app for Python extraction.
            if (not hasattr(self.app, '_aper_phot_results') or
                    not isinstance(self.app._aper_phot_results, QTable)):
                self.app._aper_phot_results = phot_table
            else:
                try:
                    phot_table['id'][0] = self.app._aper_phot_results['id'].max() + 1
                    self.app._aper_phot_results.add_row(phot_table[0])
                except Exception:  # Discard incompatible QTable
                    phot_table['id'][0] = 1
                    self.app._aper_phot_results = phot_table

            # Radial profile (Raw)
            reg_bb = phot_aperstats.bbox
            reg_ogrid = np.ogrid[reg_bb.iymin:reg_bb.iymax, reg_bb.ixmin:reg_bb.ixmax]
            radial_dx = reg_ogrid[1] - aperture.positions[0]
            radial_dy = reg_ogrid[0] - aperture.positions[1]
            radial_r = np.hypot(radial_dx, radial_dy).ravel()  # pix
            radial_img = phot_aperstats.data_cutout.data.ravel()  # data unit

            # Radial profile
            if self.current_plot_type == "Radial Profile":
                # This algorithm is from the imexam package,
                # see licenses/IMEXAM_LICENSE.txt for more details
                radial_r = list(radial_r)
                y_data = np.bincount(radial_r, radial_img) / np.bincount(radial_r)
                radial_r = np.arange(y_data.size)
                markerstyle = '--o'
                bqplot_kw = {'marker_size': 32}
            else:
                y_data = radial_img
                markerstyle = 'o'
                bqplot_kw = {'default_size': 1}

            bqplt.clear()
            # NOTE: default margin in bqplot is 60 in all directions
            fig = bqplt.figure(1, title='Radial profile from Subset center',
                               fig_margin={'top': 60, 'bottom': 60, 'left': 40, 'right': 10},
                               title_style={'font-size': '12px'})  # TODO: Jenn wants title at bottom. # noqa
            bqplt.plot(radial_r, y_data, markerstyle, figure=fig, colors='gray', **bqplot_kw)
            bqplt.xlabel(label='pix', mark=fig.marks[-1], figure=fig)
            bqplt.ylabel(label=comp.units or 'Value', mark=fig.marks[-1], figure=fig)

        except Exception as e:  # pragma: no cover
            self.reset_results()
            self.hub.broadcast(SnackbarMessage(
                f"Aperture photometry failed: {repr(e)}", color='error', sender=self))

        else:
            # Parse results for GUI.
            tmp = []
            for key in phot_table.colnames:
                if key in ('id', 'data_label', 'subset_label', 'background', 'pixarea_tot',
                           'counts_fac', 'aperture_sum_counts_err', 'flux_scaling', 'timestamp'):
                    continue
                x = phot_table[key][0]
                if (isinstance(x, (int, float, u.Quantity)) and
                        key not in ('xcentroid', 'ycentroid', 'sky_centroid', 'sum_aper_area',
                                    'aperture_sum_counts')):
                    tmp.append({'function': key, 'result': f'{x:.4e}'})
                elif key == 'sky_centroid' and x is not None:
                    tmp.append({'function': 'RA centroid', 'result': f'{x.ra.deg:.4f} deg'})
                    tmp.append({'function': 'Dec centroid', 'result': f'{x.dec.deg:.4f} deg'})
                elif key in ('xcentroid', 'ycentroid', 'sum_aper_area'):
                    tmp.append({'function': key, 'result': f'{x:.1f}'})
                elif key == 'aperture_sum_counts' and x is not None:
                    tmp.append({'function': key, 'result':
                                f'{x:.4e} ({phot_table["aperture_sum_counts_err"][0]:.4e})'})
                else:
                    tmp.append({'function': key, 'result': str(x)})
            self.results = tmp
            self.result_available = True
            self.radial_plot = fig
            self.bqplot_figs_resize = [fig]
            self.plot_available = True
