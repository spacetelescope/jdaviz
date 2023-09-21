import os
import warnings
from datetime import datetime, timezone

import astropy
import numpy as np
from astropy import units as u
from astropy.modeling.fitting import LevMarLSQFitter
from astropy.modeling import Parameter
from astropy.modeling.models import Gaussian1D
from astropy.time import Time
from glue.core.message import SubsetUpdateMessage
from ipywidgets import widget_serialization
from packaging.version import Version
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture)
from traitlets import Any, Bool, Integer, List, Unicode, observe

from jdaviz.core.events import SnackbarMessage, LinkUpdatedMessage
from jdaviz.core.region_translators import regions2aperture, _get_region_from_spatial_subset
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        SubsetSelect, TableMixin, PlotMixin)
from jdaviz.utils import PRIHDR_KEY

__all__ = ['SimpleAperturePhotometry']

ASTROPY_LT_5_2 = Version(astropy.__version__) < Version('5.2')


@tray_registry('imviz-aper-phot-simple', label="Imviz Simple Aperture Photometry")
class SimpleAperturePhotometry(PluginTemplateMixin, DatasetSelectMixin, TableMixin, PlotMixin):
    template_file = __file__, "aper_phot_simple.vue"
    subset_items = List([]).tag(sync=True)
    subset_selected = Unicode("").tag(sync=True)
    subset_area = Integer().tag(sync=True)
    bg_subset_items = List().tag(sync=True)
    bg_subset_selected = Unicode("").tag(sync=True)
    background_value = Any(0).tag(sync=True)
    pixel_area = Any(0).tag(sync=True)
    counts_factor = Any(0).tag(sync=True)
    flux_scaling = Any(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    result_failed_msg = Unicode("").tag(sync=True)
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
                                   filters=['is_spatial', 'is_not_composite', 'is_not_annulus'])

        self.bg_subset = SubsetSelect(self,
                                      'bg_subset_items',
                                      'bg_subset_selected',
                                      default_text='Manual',
                                      manual_options=['Manual'],
                                      filters=['is_spatial', 'is_not_composite'])

        headers = ['xcenter', 'ycenter', 'sky_center',
                   'sum', 'sum_aper_area',
                   'aperture_sum_counts', 'aperture_sum_counts_err',
                   'aperture_sum_mag',
                   'min', 'max', 'mean', 'median', 'mode', 'std', 'mad_std', 'var',
                   'biweight_location', 'biweight_midvariance', 'fwhm',
                   'semimajor_sigma', 'semiminor_sigma', 'orientation', 'eccentricity',
                   'data_label', 'subset_label']
        self.table.headers_avail = headers
        self.table.headers_visible = headers

        self._selected_data = None
        self._selected_subset = None
        self.plot_types = ["Curve of Growth", "Radial Profile", "Radial Profile (Raw)"]
        self.current_plot_type = self.plot_types[0]
        self._fitted_model_name = 'phot_radial_profile'

        self.plot.add_line('line', color='gray', marker_size=32)
        self.plot.add_scatter('scatter', color='gray', default_size=1)
        self.plot.add_line('fit_line', color='magenta', line_style='dashed')

        self.session.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)
        self.session.hub.subscribe(self, LinkUpdatedMessage, handler=self._on_link_update)

    @observe('dataset_selected')
    def _dataset_selected_changed(self, event={}):
        try:
            self._selected_data = self.dataset.selected_dc_item
            if self._selected_data is None:
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
                    if 'bunit_data' in meta and meta['bunit_data'] == u.Unit("MJy/sr"):
                        # Hardcode the flux conversion factor from MJy to ABmag
                        self.flux_scaling = 0.003631
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
                f"Failed to extract {self.dataset_selected}: {repr(e)}",
                color='error', sender=self))

        # Update self._selected_subset with the new self._selected_data
        # and auto-populate background, if applicable.
        self._subset_selected_changed()

    def _on_subset_update(self, msg):
        if self.dataset_selected == '' or self.subset_selected == '':
            return

        sbst = msg.subset
        if sbst.label == self.subset_selected and sbst.data.label == self.dataset_selected:
            self._subset_selected_changed()
        elif sbst.label == self.bg_subset_selected and sbst.data.label == self.dataset_selected:
            self._bg_subset_selected_changed()

    def _on_link_update(self, msg):
        if self.dataset_selected == '' or self.subset_selected == '':
            return

        # Force background auto-calculation to update when linking has changed.
        self._subset_selected_changed()

    @observe('subset_selected')
    def _subset_selected_changed(self, event={}):
        subset_selected = event.get('new', self.subset_selected)
        if self._selected_data is None or subset_selected == '':
            return

        try:
            self._selected_subset = _get_region_from_spatial_subset(
                self, self.subset.selected_subset_state)
            self._selected_subset.meta['label'] = subset_selected

            # Sky subset does not have area. Not worth it to calculate just for a warning.
            if hasattr(self._selected_subset, 'area'):
                self.subset_area = int(np.ceil(self._selected_subset.area))
            else:
                self.subset_area = 0

        except Exception as e:
            self._selected_subset = None
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {subset_selected}: {repr(e)}", color='error', sender=self))

        else:
            self._bg_subset_selected_changed()

    def _calc_bg_subset_median(self, reg):
        # Basically same way image stats are calculated in vue_do_aper_phot()
        # except here we only care about one stat for the background.
        data = self._selected_data
        comp = data.get_component(data.main_components[0])
        if hasattr(reg, 'to_pixel'):
            reg = reg.to_pixel(data.coords)
        aper_mask_stat = reg.to_mask(mode='center')
        img_stat = aper_mask_stat.get_values(comp.data, mask=None)

        # photutils/background/_utils.py --> nanmedian()
        return np.nanmedian(img_stat)  # Naturally in data unit

    @observe('bg_subset_selected')
    def _bg_subset_selected_changed(self, event={}):
        bg_subset_selected = event.get('new', self.bg_subset_selected)
        if bg_subset_selected == 'Manual':
            # we'll later access the user's self.background_value directly
            return

        try:
            reg = _get_region_from_spatial_subset(self, self.bg_subset.selected_subset_state)
            self.background_value = self._calc_bg_subset_median(reg)
        except Exception as e:
            self.background_value = 0
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {bg_subset_selected}: {repr(e)}", color='error', sender=self))

    def vue_do_aper_phot(self, *args, **kwargs):
        if self._selected_data is None or self._selected_subset is None:
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

            if hasattr(reg, 'to_pixel'):
                sky_center = reg.center
                xcenter, ycenter = data.coords.world_to_pixel(sky_center)
            else:
                xcenter = reg.center.x
                ycenter = reg.center.y
                if data.coords is not None:
                    sky_center = data.coords.pixel_to_world(xcenter, ycenter)
                else:
                    sky_center = None

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
                'id', 'sum', 'sum_aper_area',
                'min', 'max', 'mean', 'median', 'mode', 'std', 'mad_std', 'var',
                'biweight_location', 'biweight_midvariance', 'fwhm', 'semimajor_sigma',
                'semiminor_sigma', 'orientation', 'eccentricity'))  # Some cols excluded, add back as needed.  # noqa
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
                flux_scale = flux_scale * phot_table['sum'][0].unit
                sum_mag = -2.5 * np.log10(phot_table['sum'][0] / flux_scale) * u.mag
            else:
                flux_scale = None
                sum_mag = None

            # Extra info beyond photutils.
            phot_table.add_columns(
                [xcenter * u.pix, ycenter * u.pix, sky_center,
                 bg, pixarea_fac, sum_ct, sum_ct_err, ctfac, sum_mag, flux_scale, data.label,
                 reg.meta.get('label', ''), Time(datetime.now(tz=timezone.utc))],
                names=['xcenter', 'ycenter', 'sky_center', 'background', 'pixarea_tot',
                       'aperture_sum_counts', 'aperture_sum_counts_err', 'counts_fac',
                       'aperture_sum_mag', 'flux_scaling',
                       'data_label', 'subset_label', 'timestamp'],
                indexes=[1, 1, 1, 1, 3, 3, 3, 3, 3, 3, 18, 18, 18])

            try:
                phot_table['id'][0] = self.table._qtable['id'].max() + 1
                self.table.add_item(phot_table)
            except Exception:  # Discard incompatible QTable
                self.table.clear_table()
                phot_table['id'][0] = 1
                self.table.add_item(phot_table)

            # Plots.
            line = self.plot.marks['line']
            sc = self.plot.marks['scatter']
            fit_line = self.plot.marks['fit_line']

            if self.current_plot_type == "Curve of Growth":
                self.plot.figure.title = 'Curve of growth from aperture center'
                x_arr, sum_arr, x_label, y_label = _curve_of_growth(
                    comp_data, (xcenter, ycenter), aperture, phot_table['sum'][0],
                    wcs=data.coords, background=bg, pixarea_fac=pixarea_fac)
                line.x, line.y = x_arr, sum_arr
                self.plot.clear_marks('scatter', 'fit_line')
                self.plot.figure.axes[0].label = x_label
                self.plot.figure.axes[1].label = y_label

            else:  # Radial profile
                self.plot.figure.axes[0].label = 'pix'
                self.plot.figure.axes[1].label = comp.units or 'Value'

                if self.current_plot_type == "Radial Profile":
                    self.plot.figure.title = 'Radial profile from aperture center'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, (xcenter, ycenter),
                        raw=False)
                    line.x, line.y = x_data, y_data
                    self.plot.clear_marks('scatter')

                else:  # Radial Profile (Raw)
                    self.plot.figure.title = 'Raw radial profile from aperture center'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, (xcenter, ycenter),
                        raw=True)

                    sc.x, sc.y = x_data, y_data
                    self.plot.clear_marks('line')

                # Fit Gaussian1D to radial profile data.
                if self.fit_radial_profile:
                    fitter = LevMarLSQFitter()
                    y_max = y_data.max()
                    x_mean = x_data[np.where(y_data == y_max)].mean()
                    std = 0.5 * (phot_table['semimajor_sigma'][0] +
                                 phot_table['semiminor_sigma'][0])
                    if isinstance(std, u.Quantity):
                        std = std.value
                    gs = Gaussian1D(amplitude=y_max, mean=x_mean, stddev=std,
                                    fixed={'amplitude': True},
                                    bounds={'amplitude': (y_max * 0.5, y_max)})
                    if ASTROPY_LT_5_2:
                        fitter_kw = {}
                    else:
                        fitter_kw = {'filter_non_finite': True}
                    with warnings.catch_warnings(record=True) as warns:
                        fit_model = fitter(gs, x_data, y_data, **fitter_kw)
                    if len(warns) > 0:
                        msg = os.linesep.join([str(w.message) for w in warns])
                        self.hub.broadcast(SnackbarMessage(
                            f"Radial profile fitting: {msg}", color='warning', sender=self))
                    y_fit = fit_model(x_data)
                    self.app.fitted_models[self._fitted_model_name] = fit_model
                    fit_line.x, fit_line.y = x_data, y_fit
                else:
                    self.plot.clear_marks('fit_line')

        except Exception as e:  # pragma: no cover
            self.plot.clear_all_marks()
            msg = f"Aperture photometry failed: {repr(e)}"
            self.hub.broadcast(SnackbarMessage(msg, color='error', sender=self))
            self.result_failed_msg = msg
        else:
            self.result_failed_msg = ''

            # Parse results for GUI.
            tmp = []
            for key in phot_table.colnames:
                if key in ('id', 'data_label', 'subset_label', 'background', 'pixarea_tot',
                           'counts_fac', 'aperture_sum_counts_err', 'flux_scaling', 'timestamp'):
                    continue
                x = phot_table[key][0]
                if (isinstance(x, (int, float, u.Quantity)) and
                        key not in ('xcenter', 'ycenter', 'sky_center', 'sum_aper_area',
                                    'aperture_sum_counts', 'aperture_sum_mag')):
                    tmp.append({'function': key, 'result': f'{x:.4e}'})
                elif key == 'sky_center' and x is not None:
                    tmp.append({'function': 'RA center', 'result': f'{x.ra.deg:.6f} deg'})
                    tmp.append({'function': 'Dec center', 'result': f'{x.dec.deg:.6f} deg'})
                elif key in ('xcenter', 'ycenter', 'sum_aper_area'):
                    tmp.append({'function': key, 'result': f'{x:.1f}'})
                elif key == 'aperture_sum_counts' and x is not None:
                    tmp.append({'function': key, 'result':
                                f'{x:.4e} ({phot_table["aperture_sum_counts_err"][0]:.4e})'})
                elif key == 'aperture_sum_mag' and x is not None:
                    tmp.append({'function': key, 'result': f'{x:.3f}'})
                else:
                    tmp.append({'function': key, 'result': str(x)})

            # Also display fit results
            fit_tmp = []
            if fit_model is not None and isinstance(fit_model, Gaussian1D):
                for param in ('mean', 'fwhm', 'amplitude'):
                    p_val = getattr(fit_model, param)
                    if isinstance(p_val, Parameter):
                        p_val = p_val.value
                    fit_tmp.append({'function': param, 'result': f'{p_val:.4e}'})

            self.results = tmp
            self.fit_results = fit_tmp
            self.result_available = True
            self.plot_available = True

    def unpack_batch_options(self, **options):
        """
        Unpacks a dictionary of options for batch mode, including all combinations of any values
        passed as tuples or lists.  For example::

            unpack_batch_options(dataset=['image1', 'image2'],
                                 subset=['Subset 1', 'Subset 2'],
                                 bg_subset=['Subset 3'],
                                 flux_scaling=3
                                 )

        would result in::

            [{'subset': 'Subset 1',
              'dataset': 'image1',
              'bg_subset': 'Subset 3',
              'flux_scaling': 3},
             {'subset': 'Subset 2',
              'dataset': 'image1',
              'bg_subset': 'Subset 3',
              'flux_scaling': 3},
             {'subset': 'Subset 1',
              'dataset': 'image2',
              'bg_subset': 'Subset 3',
              'flux_scaling': 3},
             {'subset': 'Subset 2',
              'dataset': 'image2',
              'bg_subset': 'Subset 3',
              'flux_scaling': 3}]

        Parameters
        ----------
        options : dict
            Dictionary of values to override from the values set in the plugin/traitlets.  Each
            entry can either be a single value, or a list.  All combinations of those that contain
            a list will be exposed

        Returns
        -------
        options : list
            List of all combinations of input parameters, which can then be used as input to
            `batch_aper_phot`
        """
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
        # TODO: when enabling user API for this plugin, this should check that all inputs are
        # exposed to self.user_api (rather than the internal self)
        user_api = self  # .user_api
        invalid_keys = [k for k in options.keys() if not hasattr(user_api, k)]
        if len(invalid_keys):
            raise ValueError(f"{invalid_keys} are not valid inputs for batch photometry")

        def _is_single(v):
            if isinstance(v, (list, tuple)):
                if len(v) == 1:
                    return True, v[0]
                return False, v
            return True, v

        single_values, mult_values = {}, {}
        for k, v in options.items():
            is_single, this_value = _is_single(v)
            if is_single:
                single_values[k] = this_value
            else:
                mult_values[k] = this_value

        def _unpack_dict_list(mult_values, single_values):
            options_list = []
            # loop over the first item in mult_values
            # any remaining mult values will require recursion
            this_attr, this_values = list(mult_values.items())[0]
            remaining_mult_values = {k: v for j, (k, v) in enumerate(mult_values.items()) if j > 0}

            for this_value in this_values:
                if not len(remaining_mult_values):
                    options_list += [{this_attr: this_value, **single_values}]
                    continue
                options_list += _unpack_dict_list(remaining_mult_values,
                                                  {this_attr: this_value, **single_values})

            return options_list

        return _unpack_dict_list(mult_values, single_values)

    def batch_aper_phot(self, options, full_exceptions=False):
        """
        Run aperture photometry over a list of options.  Values will be looped in order and any
        unprovided options will remain at there previous values (either from a previous entry
        in the list or from the plugin).  The plugin itself will update and will remain at the
        final state from the last entry in the list.

        To provide a list of values per-input, use `unpack_batch_options` to and pass that as input
        here.

        Parameters
        ----------
        options : list
            Each entry will result in one computation of aperture photometry and should be
            a dictionary of values to override from the values set in the plugin/traitlets.
        full_exceptions : bool, optional
            Whether to expose the full exception message for all failed iterations.
        """
        # input validation
        if not isinstance(options, list):
            raise TypeError("options must be a list of dictionaries")
        if not np.all([isinstance(option, dict) for option in options]):
            raise TypeError("options must be a list of dictionaries")

        # these traitlets are automatically set based on the values of other traitlets in the
        # plugin, and so we should apply any user-overrides LAST
        attrs_auto_update = ('counts_factor', 'pixel_area', 'flux_scaling',
                             'subset_area', 'background_value')

        failed_iters, exceptions = [], []
        for i, option in enumerate(options):
            # NOTE: if we do not want the UI to update (and end up in the final state), then
            # we would need to refactor the plugin so that all we can compute computed values
            # from the selected dataset without necessarily observing and updating traitlets.
            # We would still want to check any select component against the valid choices.
            # We could then also skip creating/showing the plot and have a manual call to
            # vue_do_aper_phot re-enable plotting

            # order the dictionary so that items that might be automatically set based on other
            # selections are applied LATER so that user-overrides can take place.
            # NOTE: this could have non-obvious consequences if providing the override for
            # one entry but not another.  Alternatively, we could reset all traitlets to the
            # original state between each iteration of the for-loop
            option_ordered = {k: v for k, v in option.items() if k not in attrs_auto_update}
            option_ordered.update(**option)

            try:
                for attr, value in option.items():
                    # TODO: when enabling user_api, skip this and call setattr directly
                    # on self.user_api
                    if hasattr(self, f'{attr}_selected'):
                        attr = f'{attr}_selected'
                    setattr(self, attr, value)
                self.vue_do_aper_phot()
            except Exception as e:
                failed_iters.append(i)
                if full_exceptions:
                    exceptions.append(e)

        if len(failed_iters):
            err_msg = f"inputs {failed_iters} failed and were skipped."
            if full_exceptions:
                err_msg += f"  Exception messages: {exceptions}"
            else:
                err_msg += "  To see full exceptions, run individually or pass full_exceptions=True"  # noqa
            raise RuntimeError(err_msg)


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
    radial_r = np.hypot(radial_dx, radial_dy)

    # Sometimes the mask is smaller than radial_r
    if radial_cutout.shape != reg_bb.shape:
        radial_r = radial_r[:radial_cutout.shape[0], :radial_cutout.shape[1]]

    radial_r = radial_r[~radial_cutout.mask].ravel()  # pix
    radial_img = radial_cutout.compressed()  # data unit

    if raw:
        i_arr = np.argsort(radial_r)
        x_arr = radial_r[i_arr]
        y_arr = radial_img[i_arr]
    else:
        # This algorithm is from the imexam package,
        # see licenses/IMEXAM_LICENSE.txt for more details
        radial_r = np.rint(radial_r).astype(int)
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

    if hasattr(aperture, 'to_pixel'):
        aperture = aperture.to_pixel(wcs)

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
