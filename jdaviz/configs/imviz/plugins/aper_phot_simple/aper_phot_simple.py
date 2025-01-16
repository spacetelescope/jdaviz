import os
import warnings
from datetime import datetime, timezone

import numpy as np
from astropy import units as u
from astropy.modeling.fitting import TRFLSQFitter
from astropy.modeling import Parameter
from astropy.modeling.models import Gaussian1D
from astropy.time import Time
from glue.core.message import SubsetUpdateMessage
from ipywidgets import widget_serialization
from photutils.aperture import (ApertureStats, CircularAperture, EllipticalAperture,
                                RectangularAperture)
from traitlets import Any, Bool, Integer, List, Unicode, observe

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.custom_units_and_equivs import PIX2
from jdaviz.core.events import (GlobalDisplayUnitChanged, SnackbarMessage,
                                LinkUpdatedMessage, SliceValueUpdatedMessage)
from jdaviz.core.region_translators import regions2aperture, _get_region_from_spatial_subset
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetMultiSelectMixin,
                                        SubsetSelect, ApertureSubsetSelectMixin,
                                        TableMixin, PlotMixin, MultiselectMixin, with_spinner)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               check_if_unit_is_per_solid_angle,
                                               flux_conversion_general,
                                               handle_squared_flux_unit_conversions)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import PRIHDR_KEY

__all__ = ['SimpleAperturePhotometry']


@tray_registry('imviz-aper-phot-simple', label="Aperture Photometry")
class SimpleAperturePhotometry(PluginTemplateMixin, ApertureSubsetSelectMixin,
                               DatasetMultiSelectMixin, TableMixin, PlotMixin, MultiselectMixin):
    """
    The Aperture Photometry plugin performs aperture photometry for drawn regions.
    See the :ref:`Aperture Photometry Plugin Documentation <aper-phot-simple>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * :meth:`~jdaviz.core.template_mixin.TableMixin.export_table`
    * :meth:`fitted_models`
    """
    template_file = __file__, "aper_phot_simple.vue"
    uses_active_status = Bool(True).tag(sync=True)

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

    # Cubeviz only
    cube_slice = Unicode("").tag(sync=True)
    is_cube = Bool(False).tag(sync=True)

    # surface brightness display unit
    display_unit = Unicode("").tag(sync=True)

    # angle component of `display_unit`, to avoid repetition of seperating
    # it out from `display_unit`

    display_solid_angle_unit = Unicode("").tag(sync=True)

    # flux scaling display unit will always be flux, not sb. again its own
    # traitlet to avoid avoid repetition of seperating it out from `display_unit`
    flux_scaling_display_unit = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Perform aperture photometry for drawn regions.'

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
        self._fitted_models = {}
        self._fitted_model_name = 'phot_radial_profile'

        # override default plot styling
        self.plot.figure.fig_margin = {'top': 60, 'bottom': 60, 'left': 65, 'right': 15}
        self.plot.viewer.axis_y.tick_format = '0.2e'
        self.plot.viewer.axis_y.label_offset = '55px'

        self.session.hub.subscribe(self, SubsetUpdateMessage, handler=self._on_subset_update)
        self.session.hub.subscribe(self, LinkUpdatedMessage, handler=self._on_link_update)

        # Custom dataset filters for Cubeviz
        if self.config == "cubeviz":
            def valid_cubeviz_datasets(data):

                comp = data.get_component(data.main_components[0])
                img_unit = u.Unit(comp.units) if comp.units else u.dimensionless_unscaled
                solid_angle_unit = check_if_unit_is_per_solid_angle(img_unit, return_unit=True)
                if solid_angle_unit is None:  # this is encountered sometimes ??
                    return

                # multiply out solid angle so we can check physical type of numerator
                img_unit *= solid_angle_unit

                acceptable_types = ['spectral flux density wav',
                                    'photon flux density wav',
                                    'spectral flux density',
                                    'photon flux density']

                return ((data.ndim in (2, 3)) and
                        (img_unit.physical_type in acceptable_types))

            self.dataset.add_filter(valid_cubeviz_datasets)
            self.session.hub.subscribe(self, SliceValueUpdatedMessage,
                                       handler=self._on_slice_changed)

            self.hub.subscribe(self, GlobalDisplayUnitChanged,
                               handler=self._on_display_units_changed)

    @property
    def user_api(self):
        # TODO: expose public API once finalized
        # expose=('multiselect', 'dataset', 'aperture',
        #                                   'background', 'background_value',
        #                                   'pixel_area', 'counts_factor', 'flux_scaling',
        #                                   'calculate_photometry',
        #                                   'unpack_batch_options', 'calculate_batch_photometry')

        return PluginUserApi(self, expose=('export_table', 'fitted_models'))

    @property
    def fitted_models(self):
        return self._fitted_models

    def _on_slice_changed(self, msg):
        if self.config != "cubeviz":
            return
        self.cube_slice = f"{msg.value:.3e} {msg.value_unit}"
        self._cube_wave = u.Quantity(msg.value, msg.value_unit)

    @observe("dataset_selected")
    def _on_dataset_selected_changed(self, event={}):
        if self.config != "cubeviz":
            return
        # self.dataset might not exist when app is setting itself up.
        if hasattr(self, "dataset"):
            if isinstance(self.dataset.selected_dc_item, list):
                datasets = self.dataset.selected_dc_item
            else:
                datasets = [self.dataset.selected_dc_item]

            self.is_cube = False
            for dataset in datasets:
                # This assumes all cubes, or no cubes. If we allow photometry on collapsed cubes
                # or images this will need to change.
                if dataset.ndim > 2:
                    self.is_cube = True
                    break

    def _on_display_units_changed(self, event={}):

        """
        Handle change of display units from Unit Conversion plugin (for now,
        cubeviz only). If new display units differ from input data units, input
        parameters for ap. phot. (i.e background, flux scaling) are converted
        to the new units. Photometry will remain in previous unit until
        'calculate' is pressed again.
        """

        if self.config == 'cubeviz':

            # get previously selected display units
            prev_display_unit = self.display_unit
            prev_flux_scale_unit = self.flux_scaling_display_unit

            # update display unit traitlets to new selection
            self._set_display_unit_of_selected_dataset()

            # convert the previous background and flux scaling values to new unit so
            # re-calculating photometry with the current selections will produce
            # the previous output with the new unit.
            if prev_display_unit != '':

                # convert background to new unit
                if self.background_value is not None:

                    # FIXME: Kinda hacky, better solution welcomed.
                    # Basically we want to forget about PIX2 and do normal conversion.
                    # Since traitlet does not keep unit, we do not need to reapply PIX2.
                    if "pix2" in prev_display_unit and "pix2" in self.display_unit:
                        prev_unit = u.Unit(prev_display_unit) * PIX2
                        new_unit = u.Unit(self.display_unit) * PIX2
                    else:
                        prev_unit = u.Unit(prev_display_unit)
                        new_unit = u.Unit(self.display_unit)

                    if self.multiselect:
                        if len(self.dataset.selected) == 1:
                            data = self.dataset.selected_dc_item[0]
                        else:
                            raise ValueError("cannot calculate background median in multiselect")
                    else:
                        data = self.dataset.selected_dc_item

                    if prev_unit != new_unit:

                        # NOTE: I don't think all of these equivalencies are necessary,
                        # but I'm keeping them since they were already here. Background
                        # should only be converted flux<>flux or sb<>sb so only a possible
                        # u.spectral_density would be needed. explore removing these as a follow up
                        pixar_sr = data.meta.get('_pixel_scale_factor', 1.0) if data else 1.0
                        equivs = all_flux_unit_conversion_equivs(pixar_sr,
                                                                 self._cube_wave) + u.spectral()

                        self.background_value = flux_conversion_general(self.background_value,
                                                                        prev_unit,
                                                                        new_unit,
                                                                        equivs,
                                                                        with_unit=False)

                # convert flux scaling to new unit
                if self.flux_scaling is not None:

                    prev_unit = u.Unit(prev_flux_scale_unit)
                    new_unit = u.Unit(self.flux_scaling_display_unit)
                    if prev_unit != new_unit:
                        equivs = u.spectral_density(self._cube_wave)
                        self.flux_scaling = flux_conversion_general(self.flux_scaling,
                                                                    prev_unit,
                                                                    new_unit,
                                                                    equivs,
                                                                    with_unit=False)

    def _set_display_unit_of_selected_dataset(self):

        """
        Set the display_unit and flux_scaling_display_unit traitlets,
        which depend on if the selected data set is flux or surface brightness,
        and the corresponding global display unit for either flux or
        surface brightness.
        """

        # all cubes are in sb so we can get display unit for plugin from SB display unit
        # this can be changed to listen specifically to changes in surface brightness
        # from UC plugin GlobalDisplayUnitChange message, but wiill require some refactoring
        disp_unit = self.app._get_display_unit('sb')

        # this check needs to be here because 'get_display_unit' will sometimes
        # return non surface brightness units or even None when the app is starting
        # up. this can be removed once that is fixed (see PR #3144)
        if disp_unit is None or not check_if_unit_is_per_solid_angle(disp_unit):
            self.display_unit = ''
            self.flux_scaling_display_unit = ''
            return

        self.display_unit = disp_unit

        # get angle componant of surface brightness
        # note: could add 'axis=angle' when cleaning this code up to avoid repeating this

        display_solid_angle_unit = check_if_unit_is_per_solid_angle(disp_unit, return_unit=True)
        if display_solid_angle_unit is not None:
            self.display_solid_angle_unit = display_solid_angle_unit.to_string()
        else:
            # there should always be a solid angle, but i think this is
            # encountered sometimes when initializing something..
            self.display_solid_angle_unit = ''

        # flux scaling will be applied when the solid angle componant is
        # multiplied out, so use 'flux' display unit
        fs_unit = self.app._get_display_unit('flux')
        self.flux_scaling_display_unit = fs_unit

        # if cube loaded is per-pixel-squared sb (i.e flux cube loaded)
        # pixel_area should be fixed to 1
        if self.display_solid_angle_unit == 'pix2':
            self.pixel_area = 1.0

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
            # Hardcode the flux conversion factor from MJy to ABmag
            mjy2abmag = 0.003631

            # if display unit is different, translate
            if (self.config == 'cubeviz') and (self.display_unit != ''):
                disp_unit = u.Unit(self.display_unit)
                mjy2abmag = flux_conversion_general(mjy2abmag,
                                                    u.MJy / u.sr,
                                                    disp_unit,
                                                    u.spectral_density(self._cube_wave),
                                                    with_unit=False)

            if 'photometry' in meta and 'pixelarea_arcsecsq' in meta['photometry']:
                defaults['pixel_area'] = meta['photometry']['pixelarea_arcsecsq']
                if 'bunit_data' in meta and meta['bunit_data'] == u.Unit("MJy/sr"):
                    defaults['flux_scaling'] = mjy2abmag
            elif 'PIXAR_A2' in meta:
                defaults['pixel_area'] = meta['PIXAR_A2']
                if 'BUNIT' in meta and meta['BUNIT'] == u.Unit("MJy/sr"):
                    defaults['flux_scaling'] = mjy2abmag

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

        # get correct display unit for newly selected dataset
        if self.config == 'cubeviz':
            # sets display_unit and flux_scaling_display_unit traitlets
            self._set_display_unit_of_selected_dataset()

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

        if self.config == 'cubeviz':
            self._set_display_unit_of_selected_dataset()

        # NOTE: aperture_selected can be triggered here before aperture_selected_validity is updated
        # so we'll still allow the snackbar to be raised as a second warning to the user and to
        # avoid acting on outdated information

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

    @property
    def _cubeviz_slice_ind(self):
        fv = self.app.get_viewer(self.app._jdaviz_helper._default_flux_viewer_reference_name)
        return fv.slice

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

        if self.config == "cubeviz" and data.ndim > 2:
            comp_data = comp.data[:, :, self._cubeviz_slice_ind].T  # nx, ny --> ny, nx
            # Similar to coords_info logic.
            if '_orig_spec' in getattr(data, 'meta', {}):
                w = data.meta['_orig_spec'].wcs.celestial
            else:
                w = data.coords.celestial
        else:  # "imviz"
            comp_data = comp.data  # ny, nx
            w = data.coords

        if hasattr(reg, 'to_pixel'):
            reg = reg.to_pixel(w)
        aper_mask_stat = reg.to_mask(mode='center')
        img_stat = aper_mask_stat.get_values(comp_data, mask=None)

        # photutils/background/_utils.py --> nanmedian()
        bg_md = np.nanmedian(img_stat)  # Naturally in data unit

        # convert background median to display unit, if necessary (cubeviz only)
        if (self.config == 'cubeviz') and (self.display_unit != '') and comp.units:

            bg_md = flux_conversion_general(bg_md,
                                            u.Unit(comp.units),
                                            u.Unit(self.display_unit),
                                            u.spectral_density(self._cube_wave),
                                            with_unit=False)

        return bg_md

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
        Calculate aperture photometry given the values set in the plugin or
        any overrides provided as arguments here (which will temporarily
        override plugin values for this calculation only).

        Note: Values set in the plugin in Cubeviz are in the selected display unit
        from the Unit conversion plugin. Overrides are, as the docstrings note,
        assumed to be in the units of the selected dataset.

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
            Pixel area in arcsec squared, only used if data unit is a surface brightness unit.
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

        if aperture is not None:
            if aperture not in self.aperture.choices:
                raise ValueError(f"aperture must be one of {self.aperture.choices}")

        if aperture is not None or dataset is not None:
            reg = self.aperture._get_spatial_region(subset=aperture if aperture is not None else self.aperture.selected,  # noqa
                                                    dataset=dataset if dataset is not None else self.dataset.selected)  # noqa
            # determine if a valid aperture (since selected_validity only applies to selected entry)
            _, _, validity = self.aperture._get_mark_coords_and_validate(selected=aperture)
            if not validity.get('is_aperture'):
                raise ValueError(f"Selected aperture {aperture} is not valid: {validity.get('aperture_message')}")  # noqa
        else:
            # use the pre-cached value
            if not self.aperture.selected_validity.get('is_aperture'):
                raise ValueError(f"Selected aperture is not valid: {self.aperture.selected_validity.get('aperture_message')}")  # noqa
            reg = self.aperture.selected_spatial_region

        # Reset last fitted model
        fit_model = None
        # TODO: remove _fitted_model_name cache?
        if self._fitted_model_name in self._fitted_models:
            del self._fitted_models[self._fitted_model_name]

        comp = data.get_component(data.main_components[0])
        if comp.units:
            img_unit = u.Unit(comp.units)
        else:
            img_unit = None

        if self.config == 'cubeviz':
            display_unit = u.Unit(self.display_unit)

        if background is not None and background not in self.background.choices:  # pragma: no cover
            raise ValueError(f"background must be one of {self.background.choices}")
        if background_value is not None:
            if ((background not in (None, 'Manual'))
                    or (background is None and self.background_selected != 'Manual')):
                raise ValueError("cannot provide background_value with background!='Manual'")
        elif (background == 'Manual'
                or (background is None and self.background.selected == 'Manual')):

            background_value = self.background_value

            # cubeviz: background_value set in plugin is in display units
            # convert temporarily to image units for calculations
            if (self.config == 'cubeviz') and (img_unit is not None) and display_unit != '':
                background_value = flux_conversion_general(background_value,
                                                           display_unit,
                                                           img_unit,
                                                           u.spectral_density(self._cube_wave),
                                                           with_unit=False)
        elif background is None and dataset is None:

            # use the previously-computed value in the plugin
            background_value = self.background_value

            # cubeviz: background_value set in plugin is in display units
            # convert temporarily to image units for calculations
            if (self.config == 'cubeviz') and (img_unit is not None) and display_unit != '':
                background_value = flux_conversion_general(background_value,
                                                           display_unit,
                                                           img_unit,
                                                           u.spectral_density(self._cube_wave),
                                                           with_unit=False)
        else:
            bg_reg = self.aperture._get_spatial_region(subset=background if background is not None else self.background.selected,  # noqa
                                                       dataset=dataset if dataset is not None else self.dataset.selected)  # noqa
            background_value = self._calc_background_median(bg_reg, data=data)

            # cubeviz: computed background median will be in display units,
            # convert temporarily back to image units for calculations
            if (self.config == 'cubeviz') and (img_unit is not None) and display_unit != '':
                background_value = flux_conversion_general(background_value,
                                                           display_unit,
                                                           img_unit,
                                                           u.spectral_density(self._cube_wave),
                                                           with_unit=False)
        try:
            bg = float(background_value)
        except ValueError:  # Clearer error message
            raise ValueError('Missing or invalid background value')

        if self.config == "cubeviz" and data.ndim > 2:
            comp_data = comp.data[:, :, self._cubeviz_slice_ind].T  # nx, ny --> ny, nx
            # Similar to coords_info logic.
            if '_orig_spec' in getattr(data, 'meta', {}):
                w = data.meta['_orig_spec'].wcs
            else:
                w = data.coords
        else:  # "imviz"
            comp_data = comp.data  # ny, nx
            w = data.coords

        if hasattr(reg, 'to_pixel'):
            sky_center = reg.center
            if self.config == "cubeviz" and data.ndim > 2:
                ycenter, xcenter = w.world_to_pixel(self._cube_wave, sky_center)[1]
            else:  # "imviz"
                xcenter, ycenter = w.world_to_pixel(sky_center)
        else:
            xcenter = reg.center.x
            ycenter = reg.center.y
            if data.coords is not None:
                if self.config == "cubeviz" and data.ndim > 2:
                    sky_center = w.pixel_to_world(self._cubeviz_slice_ind,
                                                  ycenter, xcenter)[1]
                else:  # "imviz"
                    sky_center = w.pixel_to_world(xcenter, ycenter)
            else:
                sky_center = None

        aperture = regions2aperture(reg)
        include_pixarea_fac = False
        include_counts_fac = False
        include_flux_scale = False
        if comp.units:

            # work for now in units of currently selected dataset (which may or
            # may not be the desired output units, depending on the display
            # units selected in the Unit Conversion plugin. background value
            # has already been converted to image units above, and flux scaling
            # will be converted from display unit > img_unit
            comp_data = comp_data << img_unit
            bg = bg * img_unit

            if check_if_unit_is_per_solid_angle(img_unit):  # if units are surface brightness
                try:
                    pixarea = float(pixel_area if pixel_area is not None else self.pixel_area)
                except ValueError:  # Clearer error message
                    raise ValueError('Missing or invalid pixel area')
                if not np.allclose(pixarea, 0):
                    include_pixarea_fac = True
            if img_unit != u.count:
                try:
                    ctfac = float(counts_factor if counts_factor is not None else self.counts_factor)  # noqa: E501
                except ValueError:  # Clearer error message
                    raise ValueError('Missing or invalid counts conversion factor')
                else:
                    if ctfac < 0:
                        raise ValueError('Counts conversion factor cannot be negative '
                                         f'but got {ctfac}.')
                if not np.allclose(ctfac, 0):
                    include_counts_fac = True

            # if cubeviz and flux_scaling is provided as override, it is in the data units
            # if set in the app, it is in the display units and needs to be converted
            # if provided as an override keyword arg, it is assumed to be in the
            # data units and does not need to be converted
            if ((self.config == 'cubeviz') and (flux_scaling is None) and
                    (self.flux_scaling is not None)):

                # convert flux_scaling from flux display unit to native flux unit
                flux_scaling = flux_conversion_general(
                    self.flux_scaling,
                    u.Unit(self.flux_scaling_display_unit),
                    img_unit * u.Unit(self.display_solid_angle_unit),
                    u.spectral_density(self._cube_wave),
                    with_unit=False)

            try:
                flux_scale = float(flux_scaling if flux_scaling is not None else self.flux_scaling)
            except ValueError:  # Clearer error message
                raise ValueError('Missing or invalid flux scaling')
            if not np.allclose(flux_scale, 0):
                include_flux_scale = True

            # from now, we will just need the image unit as a string for display
            img_unit = img_unit.to_string()

        else:
            img_unit = None

        phot_aperstats = ApertureStats(comp_data, aperture, wcs=data.coords, local_bkg=bg)
        phot_table = phot_aperstats.to_table(columns=(
            'id', 'sum', 'sum_aper_area',
            'min', 'max', 'mean', 'median', 'mode', 'std', 'mad_std', 'var',
            'biweight_location', 'biweight_midvariance', 'fwhm', 'semimajor_sigma',
            'semiminor_sigma', 'orientation', 'eccentricity'))  # Some cols excluded, add back as needed.  # noqa
        rawsum = phot_table['sum'][0]

        if include_pixarea_fac:
            # convert pixarea, which is in arcsec2/pix2 to the display solid angle unit / pix2

            if self.config == 'imviz':
                # can remove once unit conversion implemented in imviz and
                # display_solid_angle_unit traitlet is set, for now it will always be the data units
                display_solid_angle_unit = check_if_unit_is_per_solid_angle(comp.units,
                                                                            return_unit=True)

            elif self.config == 'cubeviz':
                display_solid_angle_unit = u.Unit(self.display_solid_angle_unit)

            # if angle unit is pix2, pixarea should be 1 pixel2 per pixel2
            if display_solid_angle_unit == PIX2:
                pixarea_fac = 1 * PIX2
            else:
                pixarea = pixarea * (u.arcsec * u.arcsec / PIX2)
                # NOTE: Sum already has npix value encoded, so we simply apply the npix unit here.
                # don't need to go though flux_conversion_general since these units
                # arent per-pixel and won't need a workaround.
                pixarea_fac = PIX2 * pixarea.to(display_solid_angle_unit / PIX2)

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

        if self.config == "cubeviz":
            if data.ndim > 2:
                slice_val = self._cube_wave
            else:
                slice_val = u.Quantity(np.nan, self._cube_wave.unit)

            phot_table.add_column(slice_val, name="slice_wave", index=29)

            if comp.units:

                # convert units of output table to reflect display units
                # selected in Unit Conversion plugin
                display_unit = u.Unit(self.display_unit)

                # equivalencies for unit conversion, will never be flux<>sb
                # so only need spectral_density
                equivs = u.spectral_density(self._cube_wave)

                if display_unit != '':
                    if phot_table['background'].unit != display_unit:
                        bg_conv = flux_conversion_general(phot_table['background'].value,
                                                          phot_table['background'].unit,
                                                          display_unit,
                                                          equivs)
                        phot_table['background'] = bg_conv

                    phot_sum = phot_table['sum']
                    if include_pixarea_fac:
                        if phot_sum.unit != (display_unit * pixarea_fac).unit:
                            phot_table['sum'] = flux_conversion_general(phot_sum.value,
                                                                        phot_sum.unit,
                                                                        (display_unit * pixarea_fac).unit,  # noqa: E501
                                                                        equivs)

                    elif phot_sum.unit != display_unit:
                        phot_table['sum'] = flux_conversion_general(phot_sum.value,
                                                                    phot_sum.unit,
                                                                    display_unit,
                                                                    equivs)

                    for key in ['min', 'max', 'mean', 'median', 'mode', 'std',
                                'mad_std', 'biweight_location']:
                        if phot_table[key].unit != display_unit:
                            phot_table[key] = flux_conversion_general(phot_table[key].value,
                                                                      phot_table[key].unit,
                                                                      display_unit,
                                                                      equivs)

                    for key in ['var', 'biweight_midvariance']:
                        # these values will be in units of flux or surface brightness
                        # squared, so unit conversion is another special case if additional
                        # equivalencies are required
                        if phot_table[key].unit != display_unit**2:
                            conv = handle_squared_flux_unit_conversions(phot_table[key].value,
                                                                        phot_table[key].unit,
                                                                        display_unit**2,
                                                                        equivs)
                            phot_table[key] = conv

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

            # for cubeviz unit conversion display units
            if self.display_unit != '':
                plot_display_unit = self.display_unit
            else:
                plot_display_unit = None

            if self.current_plot_type == "Curve of Growth":
                if self.config == "cubeviz" and data.ndim > 2:
                    self.plot.figure.title = f'Curve of growth from aperture center at {slice_val:.4e}'  # noqa: E501
                    eqv = u.spectral_density(self._cube_wave)
                else:
                    self.plot.figure.title = 'Curve of growth from aperture center'
                    eqv = []
                x_arr, sum_arr, x_label, y_label = _curve_of_growth(
                    comp_data, (xcenter, ycenter), aperture, phot_table['sum'][0],
                    wcs=data.coords, background=bg, pixarea_fac=pixarea_fac,
                    display_unit=plot_display_unit, equivalencies=eqv)
                self.plot._update_data('profile', x=x_arr, y=sum_arr, reset_lims=True)
                self.plot.update_style('profile', line_visible=True, color='gray', size=32)
                self.plot.update_style('fit', visible=False)
                self.plot.figure.axes[0].label = x_label
                self.plot.figure.axes[1].label = y_label

            else:  # Radial profile
                self.plot.figure.axes[0].label = 'pix'
                if plot_display_unit:
                    self.plot.figure.axes[1].label = plot_display_unit
                else:
                    self.plot.figure.axes[1].label = img_unit or 'Value'

                if self.current_plot_type == "Radial Profile":
                    if self.config == "cubeviz" and data.ndim > 2:
                        self.plot.figure.title = f'Radial profile from aperture center at {slice_val:.4e}'  # noqa: E501
                        eqv = u.spectral_density(self._cube_wave)
                    else:
                        self.plot.figure.title = 'Radial profile from aperture center'
                        eqv = []
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, (xcenter, ycenter),
                        raw=False, display_unit=plot_display_unit, image_unit=img_unit,
                        equivalencies=eqv)
                    self.plot._update_data('profile', x=x_data, y=y_data, reset_lims=True)
                    self.plot.update_style('profile', line_visible=True, color='gray', size=32)

                else:  # Radial Profile (Raw)
                    if self.config == "cubeviz" and data.ndim > 2:
                        self.plot.figure.title = f'Raw radial profile from aperture center at {slice_val:.4e}'  # noqa: E501
                    else:
                        self.plot.figure.title = 'Raw radial profile from aperture center'
                    x_data, y_data = _radial_profile(
                        phot_aperstats.data_cutout, phot_aperstats.bbox, (xcenter, ycenter),
                        raw=True, display_unit=plot_display_unit, image_unit=img_unit)

                    self.plot._update_data('profile', x=x_data, y=y_data, reset_lims=True)
                    self.plot.update_style('profile', line_visible=False, color='gray', size=10)

                # Fit Gaussian1D to radial profile data.
                if self.fit_radial_profile:
                    fitter = TRFLSQFitter()
                    y_max = np.nanmax(y_data)
                    x_mean = np.nanmean(x_data[np.where(y_data == y_max)])
                    std = 0.5 * (phot_table['semimajor_sigma'][0] +
                                 phot_table['semiminor_sigma'][0])
                    if isinstance(std, u.Quantity):
                        std = std.value
                    gs = Gaussian1D(amplitude=y_max, mean=x_mean, stddev=std,
                                    fixed={'amplitude': True},
                                    bounds={'amplitude': (y_max * 0.5, y_max)})
                    with warnings.catch_warnings(record=True) as warns:
                        fit_model = fitter(gs, x_data, y_data, filter_non_finite=True)
                    if len(warns) > 0:
                        msg = os.linesep.join([str(w.message) for w in warns])
                        self.hub.broadcast(SnackbarMessage(
                            f"Radial profile fitting: {msg}", color='warning', sender=self))
                    y_fit = fit_model(x_data)
                    self._fitted_models[self._fitted_model_name] = fit_model
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

            if isinstance(x, u.Quantity):  # split up unit and value to put in different cols
                unit = x.unit.to_string()
                if unit == '':  # for eccentricity which is a quantity with an empty unit
                    unit = '-'
                x = x.value
            else:
                unit = '-'

            if (isinstance(x, (int, float)) and
                    key not in ('xcenter', 'ycenter', 'sky_center', 'sum_aper_area',
                                'aperture_sum_counts', 'aperture_sum_mag', 'slice_wave')):
                if x == 0:
                    tmp.append({'function': key, 'result': f'{x:.1f}', 'unit': unit})
                else:
                    tmp.append({'function': key, 'result': f'{x:.3e}', 'unit': unit})
            elif key == 'sky_center' and x is not None:
                tmp.append({'function': 'RA center', 'result': f'{x.ra.deg:.6f}', 'unit': 'deg'})
                tmp.append({'function': 'Dec center', 'result': f'{x.dec.deg:.6f}', 'unit': 'deg'})
            elif key in ('xcenter', 'ycenter', 'sum_aper_area'):
                tmp.append({'function': key, 'result': f'{x:.1f}', 'unit': unit})
            elif key == 'aperture_sum_counts' and x is not None:
                tmp.append({'function': key, 'result':
                            f'{x:.4e} ({phot_table["aperture_sum_counts_err"][0]:.4e})',
                            'unit': unit})
            elif key == 'aperture_sum_mag' and x is not None:
                tmp.append({'function': key, 'result': f'{x:.3f}', 'unit': unit})
            elif key == 'slice_wave':
                if data.ndim > 2:
                    tmp.append({'function': key, 'result': f'{slice_val.value:.4e}', 'unit': slice_val.unit.to_string()})  # noqa: E501
            else:
                tmp.append({'function': key, 'result': str(x), 'unit': unit})

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

def _radial_profile(radial_cutout, reg_bb, centroid, raw=False,
                    image_unit=None, display_unit=None, equivalencies=[]):
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

    image_unit : str or None
        (For cubeviz only to deal with display unit conversion). Unit of input
        'radial cutout', used with `display_unit` to convert output to desired
        display unit.

    display_unit : str or None
        (For cubeviz only to deal with display unit conversion). Desired unit
        for output.

    equivalencies : list or None
        Optional, equivalencies for unit conversion to convert radial profile
        to display unit selected in the unit conversion plugin, if it differs
        from the native data unit.

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

    if display_unit is not None:
        if image_unit is None:
            raise ValueError('Must provide image_unit with display_unit.')

        # convert array from native data unit to display unit, if they differ
        if image_unit != display_unit:
            y_arr = flux_conversion_general(y_arr,
                                            u.Unit(image_unit),
                                            u.Unit(display_unit),
                                            equivalencies=equivalencies,
                                            with_unit=False)

    return x_arr, y_arr


def _curve_of_growth(data, centroid, aperture, final_sum, wcs=None, background=0,
                     n_datapoints=10, pixarea_fac=None, display_unit=None, equivalencies=[]):
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

    display_unit : str or None
        (For cubeviz only to deal with display unit conversion). Desired unit
        for output. If unit is a surface brightness, a Flux unit will be
        returned if pixarea_fac is provided.

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

    # determined desired unit for output sum array and y label
    # cubeviz only to handle unit conversion display unit changes
    if display_unit is not None:
        sum_unit = u.Unit(display_unit)
    else:
        if isinstance(data, u.Quantity):
            sum_unit = data.unit
        else:
            sum_unit = None
    if sum_unit and pixarea_fac is not None:
        # multiply data unit by its solid angle to convert sum in sb to sum in flux
        sum_unit *= check_if_unit_is_per_solid_angle(sum_unit, return_unit=True)

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
    if isinstance(final_sum, u.Quantity):
        final_sum = flux_conversion_general(final_sum.value, final_sum.unit,
                                            sum_arr.unit, equivalencies)
    sum_arr = np.append(sum_arr, final_sum)

    if sum_unit is None:
        y_label = 'Value'
    else:
        y_label = sum_unit.to_string()
        # bqplot does not like Quantity
        sum_arr = flux_conversion_general(sum_arr.value, sum_arr.unit, sum_unit,
                                          equivalencies, with_unit=False)

    return x_arr, sum_arr, x_label, y_label
