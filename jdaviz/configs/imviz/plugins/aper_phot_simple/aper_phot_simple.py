import os
import warnings
from datetime import datetime

import bqplot
import numpy as np
from astropy import units as u
from astropy.modeling.fitting import LevMarLSQFitter
from astropy.modeling import Parameter
from astropy.modeling.models import Gaussian1D
from astropy.table import QTable
from astropy.time import Time
from glue.core.message import SubsetUpdateMessage
from ipywidgets import widget_serialization
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture)
from regions import (CircleAnnulusPixelRegion, CirclePixelRegion, EllipsePixelRegion,
                     RectanglePixelRegion)
from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.region_translators import regions2aperture
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin, DatasetSelectMixin, SubsetSelect
from jdaviz.utils import bqplot_clear_figure, PRIHDR_KEY

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(TemplateMixin, DatasetSelectMixin):
    template_file = __file__, "aper_phot_simple.vue"
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("").tag(sync=True)
    bg_subset_items = List().tag(sync=True)
    bg_subset_selected = Unicode("").tag(sync=True)
    background_value = Any(0).tag(sync=True)
    bg_annulus_inner_r = FloatHandleEmpty(0).tag(sync=True)
    bg_annulus_width = FloatHandleEmpty(10).tag(sync=True)
    pixel_area = Any(0).tag(sync=True)
    counts_factor = Any(0).tag(sync=True)
    flux_scaling = Any(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    results = List().tag(sync=True)
    plot_types = List([]).tag(sync=True)
    current_plot_type = Unicode().tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    radial_plot = Any('').tag(sync=True, **widget_serialization)
    fit_radial_profile = Bool(False).tag(sync=True)
    fit_results = List().tag(sync=True)

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
                                      manual_options=['Manual', 'Annulus'],
                                      allowed_type='spatial')

        self._selected_data = None
        self._selected_subset = None
        self._fig = bqplot.Figure()
        self.plot_types = ["Curve of Growth", "Radial Profile", "Radial Profile (Raw)"]
        self.current_plot_type = self.plot_types[0]
        self._fitted_model_name = 'phot_radial_profile'

        self.session.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)

    def reset_results(self):
        self.result_available = False
        self.results = []
        self.plot_available = False
        self.radial_plot = ''
        bqplot_clear_figure(self._fig)

    @observe('dataset_selected')
    def _dataset_selected_changed(self, event={}):
        try:
            self._selected_data = self.dataset.selected_dc_item
            if self._selected_data is None:
                self.reset_results()
                return
            self.counts_factor = 0
            self.pixel_area = 0
            self.flux_scaling = 0

            # Extract telescope specific unit conversion factors, if applicable.
            meta = self._selected_data.meta.copy()
            if PRIHDR_KEY in meta:
                meta.update(meta[PRIHDR_KEY])
                del meta[PRIHDR_KEY]
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
                f"Failed to extract {self.dataset_selected}: {repr(e)}",
                color='error', sender=self))

        # Update self._selected_subset with the new self._selected_data
        # and auto-populate background, if applicable.
        self._subset_selected_changed()

    def _get_region_from_subset(self, subset):
        for subset_grp in self.app.data_collection.subset_groups:
            if subset_grp.label == subset:
                for sbst in subset_grp.subsets:
                    if sbst.data.label == self.dataset_selected:
                        # TODO: https://github.com/glue-viz/glue-astronomy/issues/52
                        return sbst.data.get_selection_definition(
                                subset_id=subset, format='astropy-regions')
        else:
            raise ValueError(f'Subset "{subset}" not found')

    def _on_subset_update(self, msg):
        if self.dataset_selected == '' or self.subset_selected == '':
            return

        sbst = msg.subset
        if sbst.label == self.subset_selected and sbst.data.label == self.dataset_selected:
            self._subset_selected_changed()
        elif sbst.label == self.bg_subset_selected and sbst.data.label == self.dataset_selected:
            self._bg_subset_selected_changed()

    @observe('subset_selected')
    def _subset_selected_changed(self, event={}):
        subset_selected = event.get('new', self.subset_selected)
        if self._selected_data is None or subset_selected == '':
            self.reset_results()
            return

        try:
            self._selected_subset = self._get_region_from_subset(subset_selected)
            self._selected_subset.meta['label'] = subset_selected

            if isinstance(self._selected_subset, CirclePixelRegion):
                self.bg_annulus_inner_r = self._selected_subset.radius
            elif isinstance(self._selected_subset, EllipsePixelRegion):
                self.bg_annulus_inner_r = max(self._selected_subset.width,
                                              self._selected_subset.height) * 0.5
            elif isinstance(self._selected_subset, RectanglePixelRegion):
                self.bg_annulus_inner_r = np.sqrt(self._selected_subset.width ** 2 +
                                                  self._selected_subset.height ** 2) * 0.5
            else:  # pragma: no cover
                raise TypeError(f'Unsupported region shape: {self._selected_subset.__class__}')

        except Exception as e:
            self._selected_subset = None
            self.reset_results()
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {subset_selected}: {repr(e)}", color='error', sender=self))

        else:
            self._bg_subset_selected_changed()

    def _calc_bg_subset_median(self, reg):
        # Basically same way image stats are calculated in vue_do_aper_phot()
        # except here we only care about one stat for the background.
        data = self._selected_data
        comp = data.get_component(data.main_components[0])
        aper_mask_stat = reg.to_mask(mode='center')
        img_stat = aper_mask_stat.get_values(comp.data, mask=None)

        # photutils/background/_utils.py --> nanmedian()
        return np.nanmedian(img_stat)  # Naturally in data unit

    @observe('bg_annulus_inner_r', 'bg_annulus_width')
    def _bg_annulus_updated(self, *args):
        if self.bg_subset_selected != 'Annulus':
            return

        try:
            inner_r = float(self.bg_annulus_inner_r)
            reg = CircleAnnulusPixelRegion(
                self._selected_subset.center, inner_radius=inner_r,
                outer_radius=inner_r + float(self.bg_annulus_width))
            self.background_value = self._calc_bg_subset_median(reg)

        except Exception:  # Error snackbar suppressed to prevent excessive queue.
            self.background_value = 0

    @observe('bg_subset_selected')
    def _bg_subset_selected_changed(self, event={}):
        bg_subset_selected = event.get('new', self.bg_subset_selected)
        if bg_subset_selected == 'Manual':
            # we'll later access the user's self.background_value directly
            return
        if bg_subset_selected == 'Annulus':
            self._bg_annulus_updated()
            return

        try:
            reg = self._get_region_from_subset(bg_subset_selected)
            self.background_value = self._calc_bg_subset_median(reg)
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

        # Reset last fitted model
        fit_model = None
        if self._fitted_model_name in self.app.fitted_models:
            del self.app.fitted_models[self._fitted_model_name]

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

            if include_pixarea_fac:
                pixarea = pixarea * (u.arcsec * u.arcsec / (u.pix * u.pix))
                # NOTE: Sum already has npix value encoded, so we simply apply the npix unit here.
                pixarea_fac = (u.pix * u.pix) * pixarea.to(u.sr / (u.pix * u.pix))
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

            # Plots.
            # TODO: Jenn wants title at bottom.
            bqplot_clear_figure(self._fig)
            self._fig.title_style = {'font-size': '12px'}
            # NOTE: default margin in bqplot is 60 in all directions
            self._fig.fig_margin = {'top': 60, 'bottom': 60, 'left': 40, 'right': 10}
            line_x_sc = bqplot.LinearScale()
            line_y_sc = bqplot.LinearScale()

            if self.current_plot_type == "Curve of Growth":
                self._fig.title = 'Curve of growth from source centroid'
                x_arr, sum_arr, x_label, y_label = _curve_of_growth(
                    comp_data, phot_aperstats.centroid, aperture, phot_table['sum'][0],
                    wcs=data.coords, background=bg, pixarea_fac=pixarea_fac)
                self._fig.axes = [bqplot.Axis(scale=line_x_sc, label=x_label),
                                  bqplot.Axis(scale=line_y_sc, orientation='vertical',
                                              label=y_label)]
                bqplot_line = bqplot.Lines(x=x_arr, y=sum_arr, marker='circle',
                                           scales={'x': line_x_sc, 'y': line_y_sc},
                                           marker_size=32, colors='gray')
                bqplot_marks = [bqplot_line]

            else:  # Radial profile
                self._fig.axes = [bqplot.Axis(scale=line_x_sc, label='pix'),
                                  bqplot.Axis(scale=line_y_sc, orientation='vertical',
                                              label=comp.units or 'Value')]

                if self.current_plot_type == "Radial Profile":
                    self._fig.title = 'Radial profile from source centroid'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, phot_aperstats.centroid,
                        raw=False)
                    bqplot_line = bqplot.Lines(x=x_data, y=y_data, marker='circle',
                                               scales={'x': line_x_sc, 'y': line_y_sc},
                                               marker_size=32, colors='gray')
                else:  # Radial Profile (Raw)
                    self._fig.title = 'Raw radial profile from source centroid'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, phot_aperstats.centroid,
                        raw=True)
                    bqplot_line = bqplot.Scatter(x=x_data, y=y_data, marker='circle',
                                                 scales={'x': line_x_sc, 'y': line_y_sc},
                                                 default_size=1, colors='gray')

                # Fit Gaussian1D to radial profile data.
                # mean is fixed at 0 because we recentered to centroid.
                if self.fit_radial_profile:
                    fitter = LevMarLSQFitter()
                    y_max = y_data.max()
                    std = 0.5 * (phot_table['semimajor_sigma'][0] +
                                 phot_table['semiminor_sigma'][0])
                    if isinstance(std, u.Quantity):
                        std = std.value
                    gs = Gaussian1D(amplitude=y_max, mean=0, stddev=std,
                                    fixed={'mean': True, 'amplitude': True},
                                    bounds={'amplitude': (y_max * 0.5, y_max)})
                    with warnings.catch_warnings(record=True) as warns:
                        fit_model = fitter(gs, x_data, y_data)
                    if len(warns) > 0:
                        msg = os.linesep.join([str(w.message) for w in warns])
                        self.hub.broadcast(SnackbarMessage(
                            f"Radial profile fitting: {msg}", color='warning', sender=self))
                    y_fit = fit_model(x_data)
                    self.app.fitted_models[self._fitted_model_name] = fit_model
                    bqplot_fit = bqplot.Lines(x=x_data, y=y_fit, marker=None,
                                              scales={'x': line_x_sc, 'y': line_y_sc},
                                              colors='magenta', line_style='dashed')
                    bqplot_marks = [bqplot_line, bqplot_fit]
                else:
                    bqplot_marks = [bqplot_line]

            self._fig.marks = bqplot_marks

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

            # Also display fit results
            fit_tmp = []
            if fit_model is not None and isinstance(fit_model, Gaussian1D):
                for param in ('fwhm', 'amplitude'):  # mean is fixed at 0
                    p_val = getattr(fit_model, param)
                    if isinstance(p_val, Parameter):
                        p_val = p_val.value
                    fit_tmp.append({'function': param, 'result': f'{p_val:.4e}'})

            self.results = tmp
            self.fit_results = fit_tmp
            self.result_available = True
            self.radial_plot = self._fig
            self.bqplot_figs_resize = [self._fig]
            self.plot_available = True


# NOTE: These are hidden because the APIs are for internal use only
# but we need them as a separate functions for unit testing.

def _radial_profile(radial_cutout, reg_bb, centroid, raw=False):
    """Calculate radial profile.

    Parameters
    ----------
    radial_cutout : ndarray
        Cutout image from ``ApertureStats``.

    reg_bb : obj
        Bounding box from ``ApertureStats``.

    centroid : tuple of int
        ``ApertureStats`` centroid or desired center in ``(x, y)``.

    raw : bool
        If `True`, returns raw data points for scatter plot.
        Otherwise, use ``imexam`` algorithm for a clean plot.

    """
    reg_ogrid = np.ogrid[reg_bb.iymin:reg_bb.iymax, reg_bb.ixmin:reg_bb.ixmax]
    radial_dx = reg_ogrid[1] - centroid[0]
    radial_dy = reg_ogrid[0] - centroid[1]
    radial_r = np.hypot(radial_dx, radial_dy)[~radial_cutout.mask].ravel()  # pix
    radial_img = radial_cutout.compressed()  # data unit

    if raw:
        i_arr = np.argsort(radial_r)
        x_arr = radial_r[i_arr]
        y_arr = radial_img[i_arr]
    else:
        # This algorithm is from the imexam package,
        # see licenses/IMEXAM_LICENSE.txt for more details
        radial_r = list(radial_r)
        y_arr = np.bincount(radial_r, radial_img) / np.bincount(radial_r)
        x_arr = np.arange(y_arr.size)

    return x_arr, y_arr


def _curve_of_growth(data, centroid, aperture, final_sum, wcs=None, background=0, n_datapoints=10,
                     pixarea_fac=None):
    """Calculate curve of growth for aperture photometry.

    Parameters
    ----------
    data : ndarray or `~astropy.units.Quantity`
        Data for the calculation.

    centroid : tuple of int
        ``ApertureStats`` centroid or desired center in ``(x, y)``.

    aperture : obj
        ``photutils`` aperture to use, except its center will be
        changed to the given ``centroid``. This is because the aperture
        might be hand-drawn and a more accurate centroid has been
        recalculated separately.

    final_sum : float or `~astropy.units.Quantity`
        Aperture sum that is already calculated in the
        main plugin above.

    wcs : obj or `None`
        Supported WCS objects or `None`.

    background : float or `~astropy.units.Quantity`
        Background to subtract, if any. Unit must match ``data``.

    n_datapoints : int
        Number of data points in the curve.

    pixarea_fac : float or `None`
        For ``flux_unit/sr`` to ``flux_unit`` conversion.

    Returns
    -------
    x_arr : ndarray
        Data for X-axis of the curve.

    sum_arr : ndarray or `~astropy.units.Quantity`
        Data for Y-axis of the curve.

    x_label, y_label : str
        X- and Y-axis labels, respectively.

    Raises
    ------
    TypeError
        Unsupported aperture.

    """
    n_datapoints += 1  # n + 1

    if isinstance(aperture, CircularAperture):
        x_label = 'Radius (pix)'
        x_arr = np.linspace(0, aperture.r, num=n_datapoints)[1:]
        aper_list = [CircularAperture(centroid, cur_r) for cur_r in x_arr[:-1]]
    elif isinstance(aperture, EllipticalAperture):
        x_label = 'Semimajor axis (pix)'
        x_arr = np.linspace(0, aperture.a, num=n_datapoints)[1:]
        a_arr = x_arr[:-1]
        b_arr = aperture.b * a_arr / aperture.a
        aper_list = [EllipticalAperture(centroid, cur_a, cur_b, theta=aperture.theta)
                     for (cur_a, cur_b) in zip(a_arr, b_arr)]
    elif isinstance(aperture, RectangularAperture):
        x_label = 'Width (pix)'
        x_arr = np.linspace(0, aperture.w, num=n_datapoints)[1:]
        w_arr = x_arr[:-1]
        h_arr = aperture.h * w_arr / aperture.w
        aper_list = [RectangularAperture(centroid, cur_w, cur_h, theta=aperture.theta)
                     for (cur_w, cur_h) in zip(w_arr, h_arr)]
    else:
        raise TypeError(f'Unsupported aperture: {aperture}')

    sum_arr = [ApertureStats(data, cur_aper, wcs=wcs, local_bkg=background).sum
               for cur_aper in aper_list]
    if isinstance(sum_arr[0], u.Quantity):
        sum_arr = u.Quantity(sum_arr)
    else:
        sum_arr = np.array(sum_arr)
    if pixarea_fac is not None:
        sum_arr = sum_arr * pixarea_fac
    sum_arr = np.append(sum_arr, final_sum)

    if isinstance(sum_arr, u.Quantity):
        y_label = sum_arr.unit.to_string()
        sum_arr = sum_arr.value  # bqplot does not like Quantity
    else:
        y_label = 'Value'

    return x_arr, sum_arr, x_label, y_label
