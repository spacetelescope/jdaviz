from astropy.utils.decorators import deprecated

from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import AddDataMessage, SnackbarMessage
from jdaviz.core.helpers import CubeConfigHelper
from jdaviz.configs.cubeviz.plugins.viewers import CubevizImageView

__all__ = ['Cubeviz']


_spectral_axis_names = ["Wave", "Wavelength", "Freq", "Frequency",
                        "Wavenumber", "Velocity", "Energy"]


class Cubeviz(CubeConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_uncert_viewer_reference_name = "uncert-viewer"
    _default_flux_viewer_reference_name = "flux-viewer"
    _default_image_viewer_reference_name = "image-viewer"
    _cube_viewer_default_label = _default_flux_viewer_reference_name

    _loaded_flux_cube = None
    _loaded_uncert_cube = None
    _loaded_mask_cube = None
    _cube_viewer_cls = CubevizImageView

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app.hub.subscribe(self, AddDataMessage,
                               handler=self._set_spectrum_x_axis)

    def _set_spectrum_x_axis(self, msg):
        viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        if msg.viewer_id != viewer.reference_id:
            return
        ref_data = viewer.state.reference_data
        if ref_data and ref_data.ndim == 3:
            for att_name in _spectral_axis_names:
                if att_name in ref_data.component_ids():
                    if viewer.state.x_att != ref_data.id[att_name]:
                        viewer.state.x_att = ref_data.id[att_name]
                        viewer.state.reset_limits()
                    break
            else:
                viewer.state.x_att = ref_data.id["Pixel Axis 2 [x]"]
                viewer.state.reset_limits()

    def load_data(self, data, data_label=None, override_cube_limit=False, **kwargs):
        """
        Load and parse a data cube with Cubeviz.
        (Note that only one cube may be loaded per Cubeviz instance.)

        Parameters
        ----------
        data : str, `~astropy.io.fits.HDUList`, `~specutils.Spectrum1D`, or ndarray
            A string file path, astropy FITS object pointing to the
            data cube, a spectrum object, or a Numpy array cube.
            If plain array is given, axes order must be ``(x, y, z)``.
        data_label : str or `None`
            Data label to go with the given data. If not given,
            one will be automatically generated.
        override_cube_limit : bool
            Override internal cube count limitation and load the data anyway.
            Setting this to `True` is not recommended unless you know what
            you are doing.
        **kwargs : dict
            Extra keywords accepted by Jdaviz application-level parser.

        """
        if not override_cube_limit and len(self.app.state.data_items) != 0:
            raise RuntimeError('Only one cube may be loaded per Cubeviz instance')
        if data_label:
            kwargs['data_label'] = data_label

        super().load_data(data, parser_reference="cubeviz-data-parser", **kwargs)

        if 'Spectral Extraction' not in self.plugins:  # pragma: no cover
            msg = SnackbarMessage(
                "Automatic spectral extraction requires the Spectral Extraction plugin to be enabled",  # noqa
                color='error', sender=self, timeout=10000)
            self.app.hub.broadcast(msg)
        else:
            try:
                self.plugins['Spectral Extraction']._obj._extract_in_new_instance(auto_update=False, add_data=True)  # noqa
            except Exception:
                msg = SnackbarMessage(
                    "Automatic spectrum extraction for the entire cube failed."
                    " See the spectral extraction plugin to perform a custom extraction",
                    color='error', sender=self, timeout=10000)
            else:
                msg = SnackbarMessage(
                    "The extracted 1D spectrum was generated automatically for the entire cube."
                    " See the spectral extraction plugin for details or to"
                    " perform a custom extraction.",
                    color='warning', sender=self, timeout=10000)
            self.app.hub.broadcast(msg)

    @deprecated(since="4.2", alternative="plugins['Slice'].value")
    def select_wavelength(self, wavelength):
        """
        Select the slice closest to the provided wavelength.

        Parameters
        ----------
        wavelength : float
            Wavelength to select in units of the x-axis of the spectrum.  The nearest slice will
            be selected if "snap to slice" is enabled in the slice plugin.
        """
        if not isinstance(wavelength, (int, float)):
            raise TypeError("wavelength must be a float or int")
        self.select_slice(wavelength)

    @property
    def specviz(self):
        """
        A Specviz helper (:class:`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Cubeviz.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

    def get_data(self, data_label=None, spatial_subset=None, spectral_subset=None,
                 cls=None, use_display_units=False):
        """
        Returns data with name equal to ``data_label`` of type ``cls`` with subsets applied from
        ``spectral_subset``, if applicable.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spatial_subset : str, optional
            Spatial subset applied to data.  Only applicable if ``data_label`` points to a cube or
            image.  To extract a spectrum from a cube, use the spectral extraction plugin instead.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.
        use_display_units : bool, optional
            Specify whether the returned data is in native units or the current display units.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spatial_subset=spatial_subset,
                              spectral_subset=spectral_subset,
                              cls=cls, use_display_units=use_display_units)

    @deprecated(since="4.2", alternative="plugins['Aperture Photometry'].export_table()")
    def get_aperture_photometry_results(self):
        """Return aperture photometry results, if any.
        Results are calculated using :ref:`cubeviz-aper-phot` plugin.

        Returns
        -------
        results : `~astropy.table.QTable` or `None`
            Photometry results if available or `None` otherwise.

        """
        return self.plugins['Aperture Photometry'].export_table()
