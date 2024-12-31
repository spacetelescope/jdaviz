import numpy as np
import specutils
from astropy import units as u
from astropy.nddata import CCDData
from astropy.utils import minversion
from traitlets import Bool, List, Unicode, observe
from specutils import manipulation, analysis, Spectrum1D

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelect, DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin,
                                        SelectPluginComponent,
                                        SpectralContinuumMixin,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner)
from jdaviz.core.unit_conversion_utils import convert_integrated_sb_unit
from jdaviz.core.user_api import PluginUserApi

__all__ = ['MomentMap']

SPECUTILS_LT_1_15_1 = not minversion(specutils, "1.15.1.dev")

moment_unit_options = {0: ["Surface Brightness"],
                       1: ["Velocity", "Spectral Unit"],
                       2: ["Velocity", "Velocity^N"]}


@tray_registry('cubeviz-moment-maps', label="Moment Maps",
               viewer_requirements=['spectrum', 'image'])
class MomentMap(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin,
                SpectralContinuumMixin, AddResultsMixin):
    """
    See the :ref:`Moment Maps Plugin Documentation <moment-maps>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the line, or ``Entire Spectrum``.
    * ``continuum`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the continuum, or ``None`` to skip continuum subtraction,
      or ``Surrounding`` to use a region surrounding the
      subset set in ``spectral_subset``.
    * ``continuum_dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset of the extracted 1D spectrum to use when visualizing the continuum.
      The continuum will be redetermined based on the input cube (``dataset``) when
      computing the moment map.
    * ``continuum_width``:
      Width, relative to the overall line spectral region, to fit the linear continuum
      (excluding the region containing the line). If 1, will use endpoints within line region
      only.
    * ``n_moment``
    * ``output_unit``
      Choice of "Wavelength" or "Velocity", applicable for n_moment >= 1.
    * ``reference_wavelength``
      Reference wavelength for conversion of output to velocity units.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`calculate_moment`
    """
    template_file = __file__, "moment_maps.vue"
    uses_active_status = Bool(True).tag(sync=True)

    continuum_dataset_items = List().tag(sync=True)
    continuum_dataset_selected = Unicode().tag(sync=True)

    n_moment = IntHandleEmpty(0).tag(sync=True)
    filename = Unicode().tag(sync=True)
    moment_available = Bool(False).tag(sync=True)
    output_unit_items = List().tag(sync=True)
    output_radio_items = List().tag(sync=True)
    output_unit_selected = Unicode().tag(sync=True)
    reference_wavelength = FloatHandleEmpty().tag(sync=True)
    dataset_spectral_unit = Unicode().tag(sync=True)

    # export_enabled controls whether saving the moment map to a file is enabled via the UI.  This
    # is a temporary measure to allow server-installations to disable saving server-side until
    # saving client-side is supported
    export_enabled = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Create a 2D image from a data cube.'

        self.moment = None

        self.continuum_dataset = DatasetSelect(self,
                                               'continuum_dataset_items',
                                               'continuum_dataset_selected',
                                               filters=['not_child_layer',
                                                        'layer_in_spectrum_viewer'])
        # since the continuum is just an approximation preview,
        # automatically convert the units instead of recomputing
        self.continuum_auto_update_units = True

        # when plugin is initialized, there won't be a dataset selected, so
        # call the output unit 'Flux' for now (rather than surface brightness).
        # the appropriate label will be chosen once a dataset is selected, and/or
        # unit conversion is done
        self.output_unit = SelectPluginComponent(self,
                                                 items='output_unit_items',
                                                 selected='output_unit_selected',
                                                 manual_options=['Surface Brightness',
                                                                 'Spectral Unit',
                                                                 'Velocity',
                                                                 'Velocity^N'])

        self.dataset.add_filter('is_cube')
        self.add_results.viewer.filters = ['is_image_viewer']
        self.hub.subscribe(self, GlobalDisplayUnitChanged,
                           handler=self._set_data_units)

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

    @property
    def _default_image_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'flux-viewer'
        )

    @property
    def _default_spectrum_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'spectrum-viewer'
        )

    @property
    def user_api(self):
        # NOTE: leaving save_as_fits out for now - we may want a more general API to do that
        # accross all plugins at some point
        return PluginUserApi(self, expose=('dataset', 'spectral_subset',
                                           'continuum', 'continuum_dataset', 'continuum_width',
                                           'n_moment',
                                           'output_unit', 'reference_wavelength',
                                           'add_results', 'calculate_moment'))

    @property
    def slice_display_unit_name(self):
        return 'spectral'

    @observe('is_active')
    def _is_active_changed(self, msg):
        for pos, mark in self.continuum_marks.items():
            mark.visible = self.is_active
        self._calculate_continuum(msg)

    @observe("dataset_selected", "dataset_items", "n_moment")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += [f"moment {self.n_moment}"]
        self.results_label_default = " ".join(label_comps)

    @observe("dataset_selected", "n_moment")
    def _set_data_units(self, event={}):

        if isinstance(self.n_moment, str) or self.n_moment < 0:
            return
        unit_options_index = min(self.n_moment, 2)
        if self.output_unit_selected not in moment_unit_options[unit_options_index]:
            self.output_unit_selected = moment_unit_options[unit_options_index][0]
        self.send_state("output_unit_selected")

        unit_dict = {"Surface Brightness": "",
                     "Spectral Unit": "",
                     "Velocity": "km/s",
                     "Velocity^N": f"km{self.n_moment}/s{self.n_moment}"}

        if self.dataset_selected != "":
            # Spectral axis is first in this list
            data = self.app.data_collection[self.dataset_selected]
            if (self.spectrum_viewer and hasattr(self.spectrum_viewer.state, 'x_display_unit')
                    and self.spectrum_viewer.state.x_display_unit is not None):
                sunit = self.spectrum_viewer.state.x_display_unit
            elif self.app.data_collection[self.dataset_selected].coords is not None:
                sunit = data.coords.world_axis_units[0]
            else:
                sunit = ""
            self.dataset_spectral_unit = sunit
            unit_dict["Spectral Unit"] = sunit
            unit_dict["Surface Brightness"] = str(self.moment_zero_unit)

        # Update units in selection item dictionary
        for item in self.output_unit_items:
            item["unit_str"] = unit_dict[item["label"]]

        # Filter what we want based on n_moment
        if self.n_moment == 0:
            self.output_radio_items = [self.output_unit_items[0],]
        elif self.n_moment == 1:
            self.output_radio_items = self.output_unit_items[1:3]
        else:
            self.output_radio_items = self.output_unit_items[2:]

        # Force Traitlets to update
        self.send_state("output_unit_items")
        self.send_state("output_radio_items")

    @observe("dataset_selected", "spectral_subset_selected",
             "continuum_subset_selected", "continuum_dataset_selected", "continuum_width")
    @skip_if_no_updates_since_last_active()
    def _calculate_continuum(self, msg=None):
        if not hasattr(self, 'dataset') or self.app._jdaviz_helper is None:  # noqa
            # during initial init, this can trigger before the component is initialized
            return
        if self.continuum_dataset_selected == '':
            # NOTE: we could send self.dataset.selected through
            # spectral_extraction._extract_in_new_instance() to get a spectrum
            # for the selected/default cube,
            # but there is no visible spectrum to even show under the continuum
            return
        # NOTE: there is no use in caching this, as the continuum will need to be re-computed
        # per-spaxel to use within calculating the moment map
        _ = self._get_continuum(self.continuum_dataset,
                                self.spectral_subset,
                                update_marks=True)

    @with_spinner()
    def calculate_moment(self, add_data=True):
        """
        Calculate the moment map

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting data object to the app according to ``add_results``.
        """

        # Check to make sure API use hasn't put us into an invalid state.

        try:
            n_moment = int(self.n_moment)
            if n_moment < 0:
                raise ValueError("Moment must be a positive integer")
        except ValueError:
            raise ValueError("Moment must be a positive integer")

        unit_options_index = 2 if n_moment > 2 else n_moment
        if self.output_unit_selected not in moment_unit_options[unit_options_index]:
            raise ValueError("Selected output units must be in "
                             f"{moment_unit_options[unit_options_index]} for "
                             f"moment {self.n_moment}")

        if self.continuum.selected == 'None':
            if "_orig_spec" in self.dataset.selected_obj.meta:
                cube = self.dataset.selected_obj.meta["_orig_spec"]
            else:
                cube = self.dataset.selected_obj
        else:
            _, _, cube = self._get_continuum(self.continuum_dataset,
                                             self.spectral_subset,
                                             update_marks=False,
                                             per_pixel=True)

        # slice out desired region
        # TODO: should we add a warning for a composite spectral subset?
        if self.spectral_subset.selected == "Entire Spectrum":
            spec_reg = None
        else:
            spec_reg = self.app.get_subsets(self.spectral_subset.selected,
                                            simplify_spectral=True,
                                            use_display_units=True)
        # We need to convert the spectral region to the display units

        if spec_reg is None:
            slab = cube
        else:
            slab = manipulation.extract_region(cube, spec_reg)

        # Calculate the moment and convert to CCDData to add to the viewers
        # Need transpose to align JWST mirror shape: This is because specutils
        # arrange the array shape to be (nx, ny, nz) but 2D visualization
        # assumes (ny, nx) as per row-major convention.

        # Extract 2D WCS from input cube.
        data = self.dataset.selected_dc_item
        # Similar to coords_info logic.
        if '_orig_spec' in getattr(data, 'meta', {}):
            w = data.meta['_orig_spec'].wcs
        else:
            w = data.coords
        data_wcs = getattr(w, 'celestial', None)
        if data_wcs:
            data_wcs = data_wcs.swapaxes(0, 1)  # We also transpose WCS to match.

        # Convert spectral axis to velocity units if desired output is in velocity
        if n_moment > 0 and self.output_unit_selected.lower().startswith("velocity"):
            # Catch this if called from API
            if not self.reference_wavelength > 0.0:
                raise ValueError("reference_wavelength must be set for output in velocity units.")

            ref_wavelength = self.reference_wavelength * u.Unit(self.dataset_spectral_unit)
            slab_sa = slab.spectral_axis.to("km/s", doppler_convention="relativistic",
                                            doppler_rest=ref_wavelength)
            slab = Spectrum1D(slab.flux, slab_sa, uncertainty=slab.uncertainty)
        # Otherwise convert spectral axis to display units, have to do frequency <-> wavelength
        # before calculating
        else:
            slab_sa = slab.spectral_axis.to(self.app._get_display_unit('spectral'))
            slab = Spectrum1D(slab.flux, slab_sa, uncertainty=slab.uncertainty)

        # Finally actually calculate the moment
        self.moment = analysis.moment(slab, order=n_moment).T
        # If n>1 and velocity is desired, need to take nth root of result
        if n_moment > 0 and self.output_unit_selected.lower() == "velocity":
            self.moment = np.power(self.moment, 1/self.n_moment)

        # convert units for moment 0, which is the only currently supported
        # moment for using converted units.
        if n_moment == 0:
            if self.moment_zero_unit != self.moment.unit:
                spectral_axis_unit = u.Unit(self.spectrum_viewer.state.x_display_unit)

                # if the flux unit is a per-frequency unit but the spectral axis unit
                # is a wavelength, or vice versa, we need to convert the spectral axis
                # unit that the flux was integrated over so they are compatible for
                # unit conversion (e.g., Jy m / sr needs to become Jy Hz / sr, and
                # (erg Hz)/(s * cm**2 * AA) needs to become (erg)/(s * cm**2)
                desired_freq_unit = spectral_axis_unit if spectral_axis_unit.physical_type == 'frequency' else u.Hz  # noqa E501
                desired_length_unit = spectral_axis_unit if spectral_axis_unit.physical_type == 'length' else u.AA  # noqa E501
                moment_temp = convert_integrated_sb_unit(self.moment,
                                                         spectral_axis_unit,
                                                         desired_freq_unit,
                                                         desired_length_unit)
                moment_zero_unit_temp = convert_integrated_sb_unit(1 * u.Unit(self.moment_zero_unit),  # noqa E501
                                                                   spectral_axis_unit,
                                                                   desired_freq_unit,
                                                                   desired_length_unit)

                moment = moment_temp.to(moment_zero_unit_temp.unit, u.spectral())

                # if flux and spectral axis units were incompatible in terms of freq/wav
                # and needed to be converted to an intermediate unit for conversion, then
                # re-instate the original chosen units (e.g Jy m /sr was converted to Jy Hz / sr
                # for unit conversion, now back to Jy m / sr)
                if spectral_axis_unit not in moment.unit.bases:
                    if spectral_axis_unit.physical_type == 'frequency':
                        moment *= (1*desired_length_unit).to(desired_freq_unit,
                                                             u.spectral()) / desired_length_unit
                    elif spectral_axis_unit.physical_type == 'length':
                        moment *= (1*desired_freq_unit).to(desired_length_unit,
                                                           u.spectral()) / desired_freq_unit

                self.moment = moment

        # Reattach the WCS so we can load the result
        self.moment = CCDData(self.moment, wcs=data_wcs)

        fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
        self.filename = f"moment{n_moment}_{fname_label}.fits"

        if add_data:
            self.add_results.add_results_from_plugin(self.moment)

            msg = SnackbarMessage("{} added to data collection".format(self.results_label),
                                  sender=self, color="success")
            self.hub.broadcast(msg)

        self.moment_available = True

        return self.moment

    @property
    def moment_zero_unit(self):
        if self.spectrum_viewer.state.x_display_unit is not None:
            return (
                u.Unit(self.app._get_display_unit('sb')) *
                u.Unit(self.spectrum_viewer.state.x_display_unit)
            )
        return u.dimensionless_unscaled

    @property
    def spectral_unit_selected(self):
        return self.app._get_display_unit('spectral')

    def vue_calculate_moment(self, *args):
        self.calculate_moment(add_data=True)

    def vue_overwrite_fits(self, *args):
        """Attempt to force writing the moment map if the user confirms the desire to overwrite."""
        self.overwrite_warn = False
