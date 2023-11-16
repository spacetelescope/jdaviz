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
from glue_jupyter.common.toolbar_vuetify import read_icon
from ipywidgets import widget_serialization
from packaging.version import Version
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture)
from traitlets import Any, Bool, Integer, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, LinkUpdatedMessage
from jdaviz.core.region_translators import regions2aperture, _get_region_from_spatial_subset
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetMultiSelectMixin,
                                        SubsetSelect, TableMixin, PlotMixin, with_spinner)
from jdaviz.core.tools import ICON_DIR
from jdaviz.utils import PRIHDR_KEY

__all__ = ['SimpleAperturePhotometry']

ASTROPY_LT_5_2 = Version(astropy.__version__) < Version('5.2')


@tray_registry('imviz-aper-phot-simple', label="Aperture Photometry")
class SimpleAperturePhotometry(PluginTemplateMixin, DatasetMultiSelectMixin, TableMixin, PlotMixin):
    """
    The Aperture Photometry plugin performs aperture photometry for drawn regions.
    See the :ref:`Aperture Photometry Plugin Documentation <aper-phot-simple>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """
    template_file = __file__, "aper_phot_simple.vue"
    multiselect = Bool(False).tag(sync=True)

    aperture_items = List([]).tag(sync=True)
    aperture_selected = Any('').tag(sync=True)
    aperture_area = Integer().tag(sync=True)
    background_items = List().tag(sync=True)
    background_selected = Unicode("").tag(sync=True)
    background_value = FloatHandleEmpty(0).tag(sync=True)
    pixel_area_multi_auto = Bool(True).tag(sync=True)
    pixel_area = FloatHandleEmpty(0).tag(sync=True)
    counts_factor = FloatHandleEmpty(0).tag(sync=True)
    flux_scaling_multi_auto = Bool(True).tag(sync=True)
    flux_scaling_warning = Unicode("").tag(sync=True)
    flux_scaling = FloatHandleEmpty(0).tag(sync=True)
    result_available = Bool(False).tag(sync=True)
    result_failed_msg = Unicode("").tag(sync=True)
    results = List().tag(sync=True)
    plot_types = List([]).tag(sync=True)
    current_plot_type = Unicode().tag(sync=True)
    plot_available = Bool(False).tag(sync=True)
    radial_plot = Any('').tag(sync=True, **widget_serialization)
    fit_radial_profile = Bool(False).tag(sync=True)
    fit_results = List().tag(sync=True)

    icon_radialtocheck = Unicode(read_icon(os.path.join(ICON_DIR, 'radialtocheck.svg'), 'svg+xml')).tag(sync=True)  # noqa
    icon_checktoradial = Unicode(read_icon(os.path.join(ICON_DIR, 'checktoradial.svg'), 'svg+xml')).tag(sync=True)  # noqa

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.aperture = SubsetSelect(self,
                                     'aperture_items',
                                     'aperture_selected',
                                     multiselect='multiselect',
                                     dataset='dataset',
                                     default_text=None,
                                     filters=['is_spatial', 'is_not_composite', 'is_not_annulus'])

        self.background = SubsetSelect(self,
                                       'background_items',
                                       'background_selected',
                                       dataset='dataset',
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

        self.plot_types = ["Curve of Growth", "Radial Profile", "Radial Profile (Raw)"]
        self.current_plot_type = self.plot_types[0]
        self._fitted_model_name = 'phot_radial_profile'

        # override default plot styling
        self.plot.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 65, 'right': 15}
        self.plot.viewer.axis_y.tick_format = '0.2e'
        self.plot.viewer.axis_y.label_offset = '55px'

        self.session.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)
        self.session.hub.subscribe(self, LinkUpdatedMessage, handler=self._on_link_update)

# TODO: expose public API once finalized
#    @property
#    def user_api(self):
#        return PluginUserApi(self, expose=('multiselect', 'dataset', 'aperture',
#                                           'background', 'background_value',
#                                           'pixel_area', 'counts_factor', 'flux_scaling',
#                                           'calculate_photometry',
#                                           'unpack_batch_options', 'calculate_batch_photometry'))

    def _get_defaults_from_metadata(self, dataset=None):
        defaults = {}
        if dataset is None:
            meta = self.dataset.selected_dc_item.meta.copy()
        else:
            meta = self.dataset._get_dc_item(dataset).meta.copy()

        # Extract telescope specific unit conversion factors, if applicable.
        if PRIHDR_KEY in meta:
            meta.update(meta[PRIHDR_KEY])
            del meta[PRIHDR_KEY]
        if 'telescope' in meta:
            telescope = meta['telescope']
        else:
            telescope = meta.get('TELESCOP', '')
        if telescope == 'JWST':
            if 'photometry' in meta and 'pixelarea_arcsecsq' in meta['photometry']:
                defaults['pixel_area'] = meta['photometry']['pixelarea_arcsecsq']
                if 'bunit_data' in meta and meta['bunit_data'] == u.Unit("MJy/sr"):
                    # Hardcode the flux conversion factor from MJy to ABmag
                    defaults['flux_scaling'] = 0.003631
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
                    defaults['pixel_area'] = 0.05 * 0.05
                elif detector == 'hrc':  # pragma: no cover
                    defaults['pixel_area'] = 0.028 * 0.025
                elif detector == 'sbc':  # pragma: no cover
                    defaults['pixel_area'] = 0.034 * 0.03
            elif instrument == 'wfc3' and detector == 'uvis':  # pragma: no cover
                defaults['pixel_area'] = 0.04 * 0.04

        return defaults

    @observe('flux_scaling_multi_auto')
    def _multiselect_flux_scaling_warning(self, event={}):
        if not self.flux_scaling_multi_auto:
            self.flux_scaling_warning = ''
            return
        no_flux_scaling = [dataset for dataset in self.dataset.selected
                           if 'flux_scaling' not in self._get_defaults_from_metadata(dataset)]
        if len(no_flux_scaling):
            self.flux_scaling_warning = ('Could not determine flux scaling for '
                                         f'{", ".join(no_flux_scaling)}.  Those entries will '
                                         'default to zero.  Turn off auto-mode to provide '
                                         'flux-scaling manually.')
        else:
            self.flux_scaling_warning = ''

    @observe('flux_scaling')
    def _singleselect_flux_scaling_warning(self, event={}):
        if not self.multiselect:
            # disable warning once user changes value
            self.flux_scaling_warning = ''

    @observe('dataset_selected')
    def _dataset_selected_changed(self, event={}):
        if not hasattr(self, 'dataset'):
            # plugin not fully initialized
            return
        if self.dataset.selected_dc_item is None:
            return
        if self.multiselect:
            # defaults are applied within the loop if the auto-switches are enabled,
            # but we still need to update the flux-scaling warning
            self._multiselect_flux_scaling_warning()
            return

        try:
            defaults = self._get_defaults_from_metadata()
            self.counts_factor = 0
            self.pixel_area = defaults.get('pixel_area', 0)
            self.flux_scaling = defaults.get('flux_scaling', 0)
            if 'flux_scaling' in defaults:
                self.flux_scaling_warning = ''
            else:
                self.flux_scaling_warning = ('Could not determine flux scaling for '
                                             f'{self.dataset.selected}, defaulting to zero.')

        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {self.dataset_selected}: {repr(e)}",
                color='error', sender=self))

        # auto-populate background, if applicable.
        self._aperture_selected_changed()

    def _on_subset_update(self, msg):
        if not self.dataset_selected or not self.aperture_selected:
            return
        if self.multiselect:
            self._background_selected_changed()
            return

        sbst = msg.subset
        if sbst.label == self.aperture_selected and sbst.data.label == self.dataset_selected:
            self._aperture_selected_changed()
        elif sbst.label == self.background_selected and sbst.data.label == self.dataset_selected:
            self._background_selected_changed()

    def _on_link_update(self, msg):
        if not self.dataset_selected or not self.aperture_selected:
            return

        # Force background auto-calculation to update when linking has changed.
        self._aperture_selected_changed()

    @observe('aperture_selected', 'multiselect')
    def _aperture_selected_changed(self, event={}):
        if not self.dataset_selected or not self.aperture_selected:
            return
        if self.multiselect is not isinstance(self.aperture_selected, list):
            # then multiselect is in the process of changing but the traitlet for aperture_selected
            # has not been updated internally yet
            return
        if self.multiselect:
            self._background_selected_changed()
            return

        # NOTE: aperture area is only used to determine if a warning should be shown in the UI
        # and so does not need to be calculated within user API calls that don't act on traitlets
        try:
            # Sky subset does not have area. Not worth it to calculate just for a warning.
            if hasattr(self.aperture.selected_spatial_region, 'area'):
                self.aperture_area = int(np.ceil(self.aperture.selected_spatial_region.area))
            else:
                self.aperture_area = 0
        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {self.aperture_selected}: {repr(e)}",
                color='error', sender=self))
        else:
            self._background_selected_changed()

    def _calc_background_median(self, reg, data=None):
        # Basically same way image stats are calculated in vue_do_aper_phot()
        # except here we only care about one stat for the background.
        if data is None:
            if self.multiselect:
                if len(self.dataset.selected) == 1:
                    data = self.dataset.selected_dc_item[0]
                else:
                    raise ValueError("cannot calculate background median in multiselect")
            else:
                data = self.dataset.selected_dc_item
        comp = data.get_component(data.main_components[0])
        if hasattr(reg, 'to_pixel'):
            reg = reg.to_pixel(data.coords)
        aper_mask_stat = reg.to_mask(mode='center')
        img_stat = aper_mask_stat.get_values(comp.data, mask=None)

        # photutils/background/_utils.py --> nanmedian()
        return np.nanmedian(img_stat)  # Naturally in data unit

    @observe('background_selected')
    def _background_selected_changed(self, event={}):
        background_selected = event.get('new', self.background_selected)
        if background_selected == 'Manual':
            # we'll later access the user's self.background_value directly
            return

        if self.multiselect:
            # background_value will be recomputed within batch mode anyways and will
            # be replaced in the UI with a message
            self.background_value = -1
            return

        try:
            reg = _get_region_from_spatial_subset(self, self.background.selected_subset_state)
            self.background_value = self._calc_background_median(reg)
        except Exception as e:
            self.background_value = 0
            self.hub.broadcast(SnackbarMessage(
                f"Failed to extract {background_selected}: {repr(e)}", color='error', sender=self))

    @with_spinner()
    def calculate_photometry(self, dataset=None, aperture=None, background=None,
                             background_value=None, pixel_area=None, counts_factor=None,
                             flux_scaling=None, add_to_table=True, update_plots=True):
        """
        Calculate aperture photometry given the values set in the plugin or any overrides provided
        as arguments here (which will temporarily override plugin values for this calculation only).

        Parameters
        ----------
        dataset : str, optional
            Dataset to use for photometry.
        aperture : str, optional
            Subset to use as the aperture.
        background : str, optional
            Subset to use to calculate the background.
        background_value : float, optional
            Background to subtract, same unit as data.  Automatically computed if ``background``
            is set to a subset.
        pixel_area : float, optional
            Pixel area in arcsec squared, only used if sr in data unit.
        counts_factor : float, optional
            Factor to convert data unit to counts, in unit of flux/counts.
        flux_scaling : float, optional
            Same unit as data, used in -2.5 * log(flux / flux_scaling).
        add_to_table : bool, optional
        update_plots : bool, optional

        Returns
        -------
        table row, fit results
        """
        if self.multiselect and (dataset is None or aperture is None):  # pragma: no cover
            raise ValueError("for batch mode, use calculate_batch_photometry")

        if dataset is not None:
            if dataset not in self.dataset.choices:  # pragma: no cover
                raise ValueError(f"dataset must be one of {self.dataset.choices}")
            data = self.dataset._get_dc_item(dataset)
        else:
            # we can use the pre-cached value
            data = self.dataset.selected_dc_item

        if aperture is not None and aperture not in self.aperture.choices:
            raise ValueError(f"aperture must be one of {self.aperture.choices}")
        if aperture is not None or dataset is not None:
            reg = self.aperture._get_spatial_region(subset=aperture if aperture is not None else self.aperture.selected,  # noqa
                                                    dataset=dataset if dataset is not None else self.dataset.selected)  # noqa
        else:
            # use the pre-cached value
            reg = self.aperture.selected_spatial_region

        # Reset last fitted model
        fit_model = None
        # TODO: remove _fitted_model_name cache?
        if self._fitted_model_name in self.app.fitted_models:
            del self.app.fitted_models[self._fitted_model_name]

        comp = data.get_component(data.main_components[0])

        if background is not None and background not in self.background.choices:  # pragma: no cover
            raise ValueError(f"background must be one of {self.background.choices}")
        if background_value is not None:
            if ((background not in (None, 'Manual'))
                    or (background is None and self.background_selected != 'Manual')):
                raise ValueError("cannot provide background_value with background!='Manual'")
        elif (background == 'Manual'
                or (background is None and self.background.selected == 'Manual')):
            background_value = self.background_value
        elif background is None and dataset is None:
            # use the previously-computed value in the plugin
            background_value = self.background_value
        else:
            bg_reg = self.aperture._get_spatial_region(subset=background if background is not None else self.background.selected,  # noqa
                                                       dataset=dataset if dataset is not None else self.dataset.selected)  # noqa
            background_value = self._calc_background_median(bg_reg, data=data)
        try:
            bg = float(background_value)
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
                    pixarea = float(pixel_area if pixel_area is not None else self.pixel_area)
                except ValueError:  # Clearer error message
                    raise ValueError('Missing or invalid pixel area')
                if not np.allclose(pixarea, 0):
                    include_pixarea_fac = True
            if img_unit != u.count:
                try:
                    ctfac = float(counts_factor if counts_factor is not None else self.counts_factor)  # noqa
                except ValueError:  # Clearer error message
                    raise ValueError('Missing or invalid counts conversion factor')
                if not np.allclose(ctfac, 0):
                    include_counts_fac = True
            try:
                flux_scale = float(flux_scaling if flux_scaling is not None else self.flux_scaling)
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

        if add_to_table:
            try:
                phot_table['id'][0] = self.table._qtable['id'].max() + 1
                self.table.add_item(phot_table)
            except Exception:  # Discard incompatible QTable
                self.table.clear_table()
                phot_table['id'][0] = 1
                self.table.add_item(phot_table)

            # User wants 'sum' as scientific notation.
            self.table._qtable['sum'].info.format = '.6e'

        # Plots.
        if update_plots:
            if self.current_plot_type == "Curve of Growth":
                self.plot.figure.title = 'Curve of growth from aperture center'
                x_arr, sum_arr, x_label, y_label = _curve_of_growth(
                    comp_data, (xcenter, ycenter), aperture, phot_table['sum'][0],
                    wcs=data.coords, background=bg, pixarea_fac=pixarea_fac)
                self.plot._update_data('profile', x=x_arr, y=sum_arr, reset_lims=True)
                self.plot.update_style('profile', line_visible=True, color='gray', size=32)
                self.plot.update_style('fit', visible=False)
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
                    self.plot._update_data('profile', x=x_data, y=y_data, reset_lims=True)
                    self.plot.update_style('profile', line_visible=True, color='gray', size=32)

                else:  # Radial Profile (Raw)
                    self.plot.figure.title = 'Raw radial profile from aperture center'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, (xcenter, ycenter),
                        raw=True)

                    self.plot._update_data('profile', x=x_data, y=y_data, reset_lims=True)
                    self.plot.update_style('profile', line_visible=False, color='gray', size=10)

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
                    self.plot._update_data('fit', x=x_data, y=y_fit, reset_lims=True)
                    self.plot.update_style('fit', color='magenta',
                                           markers_visible=False, line_visible=True)
                else:
                    self.plot.update_style('fit', visible=False)

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

        if update_plots:
            # Also display fit results
            fit_tmp = []
            if fit_model is not None and isinstance(fit_model, Gaussian1D):
                for param in ('mean', 'fwhm', 'amplitude'):
                    p_val = getattr(fit_model, param)
                    if isinstance(p_val, Parameter):
                        p_val = p_val.value
                    fit_tmp.append({'function': param, 'result': f'{p_val:.4e}'})

        self.results = tmp
        self.result_available = True

        if update_plots:
            self.fit_results = fit_tmp
            self.plot_available = True

        return phot_table, fit_model

    def vue_do_aper_phot(self, *args, **kwargs):
        if self.dataset_selected == '' or self.aperture_selected == '':
            self.hub.broadcast(SnackbarMessage(
                "No data for aperture photometry", color='error', sender=self))
            return

        try:
            if self.multiselect:
                # even though plots aren't show in the UI when in multiselect mode,
                # we'll create the last entry so if multiselect is disabled, the last
                # iteration will show and not result in confusing behavior
                self.calculate_batch_photometry(add_to_table=True, update_plots=True)
            else:
                self.calculate_photometry(add_to_table=True, update_plots=True)
        except Exception as e:  # pragma: no cover
            self.plot.clear_all_marks()
            msg = f"Aperture photometry failed: {repr(e)}"
            self.hub.broadcast(SnackbarMessage(msg, color='error', sender=self))
            self.result_failed_msg = msg
        else:
            self.result_failed_msg = ''

    def unpack_batch_options(self, **options):
        """
        Unpacks a dictionary of options for batch mode, including all combinations of any values
        passed as tuples or lists.  For example::

            unpack_batch_options(dataset=['image1', 'image2'],
                                 aperture=['Subset 1', 'Subset 2'],
                                 background=['Subset 3'],
                                 flux_scaling=3
                                 )

        would result in::

            [{'aperture': 'Subset 1',
              'dataset': 'image1',
              'background': 'Subset 3',
              'flux_scaling': 3},
             {'aperture': 'Subset 2',
              'dataset': 'image1',
              'background': 'Subset 3',
              'flux_scaling': 3},
             {'aperture': 'Subset 1',
              'dataset': 'image2',
              'background': 'Subset 3',
              'flux_scaling': 3},
             {'aperture': 'Subset 2',
              'dataset': 'image2',
              'background': 'Subset 3',
              'flux_scaling': 3}]

        Parameters
        ----------
        options : dict, optional
            Dictionary of values to override from the values set in the plugin/traitlets.  Each
            entry can either be a single value, or a list.  All combinations of those that contain
            a list will be exposed.  If not provided and the plugin is in multiselect mode
            (``multiselect = True``), then the current values set in the plugin will be used.

        Returns
        -------
        options : list
            List of all combinations of input parameters, which can then be used as input to
            `calculate_batch_photometry`.
        """
        if not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
        if not options:
            if not self.multiselect:  # pragma: no cover
                raise ValueError("must either provide a dictionary or set plugin to multiselect mode")  # noqa
            options = {'dataset': self.dataset.selected, 'aperture': self.aperture.selected}

        # TODO: use self.user_api once API is made public
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
            if not len(mult_values):
                return [single_values]
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

    @with_spinner()
    def calculate_batch_photometry(self, options=[], add_to_table=True, update_plots=True,
                                   full_exceptions=False):
        """
        Run aperture photometry over a list of options.  Unprovided options will remain at their
        values defined in the plugin.

        To provide a list of values per-input, use `unpack_batch_options` to and pass that as input
        here.

        Parameters
        ----------
        options : list
            Each entry will result in one computation of aperture photometry and should be
            a dictionary of values to override from the values set in the plugin/traitlets.
        add_to_table : bool
            Whether to add results to the plugin table.
        update_plots : bool
            Whether to update the plugin plots for the last iteration.
        full_exceptions : bool, optional
            Whether to expose the full exception message for all failed iterations.
        """
        # input validation
        if not isinstance(options, list):
            raise TypeError("options must be a list of dictionaries")
        if not np.all([isinstance(option, dict) for option in options]):
            raise TypeError("options must be a list of dictionaries")
        if not len(options):
            if not self.multiselect:  # pragma: no cover
                raise ValueError("must either provide manual options or put the plugin in multiselect mode")  # noqa
            # unpack the batch options as provided in the app
            options = self.unpack_batch_options()

        failed_iters, exceptions = [], []
        for i, option in enumerate(options):
            # only update plots on the last iteration
            this_update_plots = i == len(options) and update_plots
            defaults = self._get_defaults_from_metadata(option.get('dataset',
                                                                   self.dataset.selected))
            if self.pixel_area_multi_auto:
                option.setdefault('pixel_area', defaults.get('pixel_area', 0))
            if self.flux_scaling_multi_auto:
                option.setdefault('flux_scaling', defaults.get('flux_scaling', 0))
            try:
                self.calculate_photometry(add_to_table=add_to_table,
                                          update_plots=this_update_plots,
                                          **option)
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
