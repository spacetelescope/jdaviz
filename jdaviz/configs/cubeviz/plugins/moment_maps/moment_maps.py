import os
from pathlib import Path

from astropy import units as u
from astropy.nddata import CCDData

from traitlets import Unicode, Bool, observe
from specutils import Spectrum1D, manipulation, analysis

from jdaviz.core.custom_traitlets import IntHandleEmpty
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin)
from jdaviz.core.user_api import PluginUserApi

__all__ = ['MomentMap']


spaxel = u.def_unit('spaxel', 1 * u.Unit(""))
u.add_enabled_units([spaxel])


@tray_registry('cubeviz-moment-maps', label="Moment Maps",
               viewer_requirements=['spectrum', 'image'])
class MomentMap(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin,
                AddResultsMixin):
    """
    See the :ref:`Moment Maps Plugin Documentation <moment-maps>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``dataset`` (:class:`~jdaviz.core.template_mixin.DatasetSelect`):
      Dataset to use for computing line statistics.
    * ``spectral_subset`` (:class:`~jdaviz.core.template_mixin.SubsetSelect`):
      Subset to use for the line, or ``Entire Spectrum``.
    * ``n_moment``
    * ``add_results`` (:class:`~jdaviz.core.template_mixin.AddResults`)
    * :meth:`calculate_moment`
    """
    template_file = __file__, "moment_maps.vue"

    n_moment = IntHandleEmpty(0).tag(sync=True)
    filename = Unicode().tag(sync=True)
    moment_available = Bool(False).tag(sync=True)
    overwrite_warn = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        self._default_image_viewer_reference_name = kwargs.get(
            "image_viewer_reference_name", "image-viewer"
        )
        super().__init__(*args, **kwargs)

        self.moment = None

        self.dataset.add_filter('is_cube')
        self.add_results.viewer.filters = ['is_image_viewer']

    @property
    def user_api(self):
        # NOTE: leaving save_as_fits out for now - we may want a more general API to do that
        # accross all plugins at some point
        return PluginUserApi(self, expose=('dataset', 'spectral_subset', 'n_moment',
                                           'add_results', 'calculate_moment'))

    @observe("dataset_selected", "dataset_items", "n_moment")
    def _set_default_results_label(self, event={}):
        label_comps = []
        if hasattr(self, 'dataset') and len(self.dataset.labels) > 1:
            label_comps += [self.dataset_selected]
        label_comps += [f"moment {self.n_moment}"]
        self.results_label_default = " ".join(label_comps)

    def calculate_moment(self, add_data=True):
        """
        Calculate the moment map

        Parameters
        ----------
        add_data : bool
            Whether to add the resulting data object to the app according to ``add_results``.
        """
        # Retrieve the data cube and slice out desired region, if specified
        cube = self.dataset.get_object(cls=Spectrum1D, statistic=None)
        spec_min, spec_max = self.spectral_subset.selected_min_max(cube)
        slab = manipulation.spectral_slab(cube, spec_min, spec_max)

        # Calculate the moment and convert to CCDData to add to the viewers
        try:
            n_moment = int(self.n_moment)
            if n_moment < 0:
                raise ValueError("Moment must be a positive integer")
        except ValueError:
            raise ValueError("Moment must be a positive integer")
        # Need transpose to align JWST mirror shape: This is because specutils
        # arrange the array shape to be (nx, ny, nz) but 2D visualization
        # assumes (ny, nx) as per row-major convention.
        data_wcs = getattr(cube.wcs, 'celestial', None)
        if data_wcs:
            data_wcs = data_wcs.swapaxes(0, 1)  # We also transpose WCS to match.
        self.moment = CCDData(analysis.moment(slab, order=n_moment).T, wcs=data_wcs)

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
