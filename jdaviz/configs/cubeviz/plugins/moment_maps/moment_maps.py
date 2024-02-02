import os
from pathlib import Path

from astropy import units as u
from astropy.nddata import CCDData
import numpy as np

from traitlets import Bool, List, Unicode, observe
from specutils import manipulation, analysis, Spectrum1D

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin,
                                        SelectPluginComponent,
                                        SpectralContinuumMixin,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['MomentMap']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])

moment_unit_options = {0: ["Flux"],
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

    n_moment = IntHandleEmpty(0).tag(sync=True)
    filename = Unicode().tag(sync=True)
    moment_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)
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

        self.moment = None

        self.output_unit = SelectPluginComponent(self,
                                                 items='output_unit_items',
                                                 selected='output_unit_selected',
                                                 manual_options=['Flux', 'Spectral Unit',
                                                                 'Velocity', 'Velocity^N'])

        self.dataset.add_filter('is_cube')
        self.add_results.viewer.filters = ['is_image_viewer']

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
                                           'continuum', 'continuum_width',
                                           'n_moment',
                                           'output_unit', 'reference_wavelength',
                                           'add_results', 'calculate_moment'))

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
        unit_options_index = 2 if self.n_moment > 2 else self.n_moment
        if self.output_unit_selected not in moment_unit_options[unit_options_index]:
            self.output_unit_selected = moment_unit_options[unit_options_index][0]
        self.send_state("output_unit_selected")

        unit_dict = {"Flux": "",
                     "Spectral Unit": "",
                     "Velocity": "km/s",
                     "Velocity^N": f"km{self.n_moment}/s{self.n_moment}"}

        if self.dataset_selected != "":
            # Spectral axis is first in this list
            data = self.app.data_collection[self.dataset_selected]
            if self.app.data_collection[self.dataset_selected].coords is not None:
                sunit = data.coords.world_axis_units[0]
                self.dataset_spectral_unit = sunit
                unit_dict["Spectral Unit"] = sunit
            else:
                self.dataset_spectral_unit = ""
            unit_dict["Flux"] = data.get_component('flux').units

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
             "continuum_subset_selected", "continuum_width")
    @skip_if_no_updates_since_last_active()
    def _calculate_continuum(self, msg=None):
        if not hasattr(self, 'dataset') or self.app._jdaviz_helper is None:  # noqa
            # during initial init, this can trigger before the component is initialized
            return

        # NOTE: there is no use in caching this, as the continuum will need to be re-computed
        # per-spaxel to use within calculating the moment map
        _ = self._get_continuum(self.dataset,
                                None,
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
            _, _, cube = self._get_continuum(self.dataset,
                                             'per-pixel',
                                             self.spectral_subset,
                                             update_marks=False)

        # slice out desired region
        # TODO: should we add a warning for a composite spectral subset?
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)
        slab = manipulation.spectral_slab(cube, spec_min, spec_max)

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
            slab = Spectrum1D(slab.flux, slab_sa)

        # Finally actually calculate the moment
        self.moment = analysis.moment(slab, order=n_moment).T
        # If n>1 and velocity is desired, need to take nth root of result
        if n_moment > 0 and self.output_unit_selected.lower() == "velocity":
            self.moment = np.power(self.moment, 1/self.n_moment)
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

    def vue_calculate_moment(self, *args):
        self.calculate_moment(add_data=True)

    def vue_save_as_fits(self, *args):
        self._write_moment_to_fits()

    def vue_overwrite_fits(self, *args):
        """Attempt to force writing the moment map if the user confirms the desire to overwrite."""
        self.overwrite_warn = False
        self._write_moment_to_fits(overwrite=True)

    def _write_moment_to_fits(self, overwrite=False, *args):
        if self.moment is None or not self.filename:  # pragma: no cover
            return
        if not self.export_enabled:
            # this should never be triggered since this is intended for UI-disabling and the
            # UI section is hidden, but would prevent any JS-hacking
            raise ValueError("Writing out moment map to file is currently disabled")

        # Make sure file does not end up in weird places in standalone mode.
        path = os.path.dirname(self.filename)
        if path and not os.path.exists(path):
            raise ValueError(f"Invalid path={path}")
        elif (not path or path.startswith("..")) and os.environ.get("JDAVIZ_START_DIR", ""):  # noqa: E501 # pragma: no cover
            filename = Path(os.environ["JDAVIZ_START_DIR"]) / self.filename
        else:
            filename = Path(self.filename).resolve()

        if filename.exists():
            if overwrite:
                # Try to delete the file
                filename.unlink()
                if filename.exists():
                    # Warn the user if the file still exists
                    raise FileExistsError(f"Unable to delete {filename}. Check user permissions.")
            else:
                self.overwrite_warn = True
                return

        filename = str(filename)
        self.moment.write(filename)

        # Let the user know where we saved the file.
        self.hub.broadcast(SnackbarMessage(
            f"Moment map saved to {os.path.abspath(filename)}", sender=self, color="success"))
