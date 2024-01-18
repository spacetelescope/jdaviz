import os
from pathlib import Path
import warnings

from astropy.nddata import CCDData
from glue.core import Data
from specutils.manipulation import spectral_slab
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SelectPluginComponent,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin,
                                        with_spinner)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['Collapse']


@tray_registry('g-collapse', label="Collapse", viewer_requirements='spectrum')
class Collapse(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin, AddResultsMixin):
    """
    See the :ref:`Collapse Plugin Documentation <collapse>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the line, or ``Entire Spectrum``.
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`collapse`
    """
    template_file = __file__, "collapse.vue"
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)
    filename = Unicode().tag(sync=True)
    collapsed_spec_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)
    # export_enabled controls whether saving to a file is enabled via the UI.  This
    # is a temporary measure to allow server-installations to disable saving server-side until
    # saving client-side is supported
    export_enabled = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self._label_counter = 0

        self.collapsed_spec = None

        self.function = SelectPluginComponent(self,
                                              items='function_items',
                                              selected='function_selected',
                                              manual_options=['Mean', 'Median', 'Min', 'Max', 'Sum'])  # noqa

        self.dataset.add_filter('is_cube')
        self.add_results.viewer.filters = ['is_image_viewer']

        if self.app.state.settings.get('server_is_remote', False):
            # when the server is remote, saving the file in python would save on the server, not
            # on the user's machine, so export support in cubeviz should be disabled
            self.export_enabled = False

    @property
    def _default_spectrum_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_viewer_reference_name

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('dataset', 'function', 'spectral_subset',
                                           'add_results', 'collapse'))

    @observe("dataset_selected", "dataset_items")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += ["collapsed"]
        self.results_label_default = " ".join(label_comps)

    @with_spinner()
    def collapse(self, add_data=True):
        """
        Collapse over the spectral axis.

        Parameters
        ----------
        add_data : bool
            Whether to load the resulting data back into the application according to
            ``add_results``.
        """
        # Collapsing over the spectral axis. Cut out the desired spectral
        # region. Defaults to the entire spectrum.
        cube = self.dataset.selected_obj
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)

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

        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='No observer defined on WCS')
            spec = spectral_slab(cube, spec_min, spec_max)
            # Spatial-spatial image only.
            collapsed_spec = spec.collapse(self.function_selected.lower(), axis=-1).T  # Quantity

            # stuff for exporting to file
            self.collapsed_spec = CCDData(collapsed_spec, wcs=data_wcs)
            self.collapsed_spec_available = True
            fname_label = self.dataset_selected.replace("[", "_").replace("]", "")
            self.filename = f"collapsed_{self.function_selected.lower()}_{fname_label}.fits"

        if add_data:
            data = Data(coords=data_wcs)
            data['flux'] = collapsed_spec.value
            data.get_component('flux').units = collapsed_spec.unit.to_string()

            self.add_results.add_results_from_plugin(data)

            snackbar_message = SnackbarMessage(
                f"Data set '{self.dataset_selected}' collapsed successfully.",
                color="success",
                sender=self)
            self.hub.broadcast(snackbar_message)

        return collapsed_spec

    def vue_collapse(self, *args, **kwargs):
        self.collapse(add_data=True)

    def vue_save_as_fits(self, *args):
        self._save_collapsed_spec_to_fits()

    def vue_overwrite_fits(self, *args):
        """Attempt to force writing the file if the user confirms the desire to overwrite."""
        self.overwrite_warn = False
        self._save_collapsed_spec_to_fits(overwrite=True)

    def _save_collapsed_spec_to_fits(self, overwrite=False, *args):

        if not self.export_enabled:
            # this should never be triggered since this is intended for UI-disabling and the
            # UI section is hidden, but would prevent any JS-hacking
            raise ValueError("Writing out collapsed cube to file is currently disabled")

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
        self.collapsed_spec.write(filename)

        # Let the user know where we saved the file.
        self.hub.broadcast(SnackbarMessage(
            f"Collapsed cube saved to {os.path.abspath(filename)}",
                           sender=self, color="success"))
