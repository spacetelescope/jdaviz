from jdaviz.core.helpers import CubeConfigHelper
from jdaviz.core.events import SliceSelectSliceMessage

__all__ = ['Rampviz']


class Rampviz(CubeConfigHelper):
    """Rampviz Helper class"""
    _default_configuration = 'rampviz'
    _default_profile_viewer_reference_name = "integration-viewer"
    _default_diff_viewer_reference_name = "diff-viewer"
    _default_group_viewer_reference_name = "group-viewer"
    _default_image_viewer_reference_name = "image-viewer"

    _loaded_flux_cube = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def load_data(self, data, data_label=None, override_cube_limit=False, **kwargs):
        """
        Load and parse a data cube with Cubeviz.
        (Note that only one cube may be loaded per Cubeviz instance.)

        Parameters
        ----------
        data : str, `~astropy.io.fits.HDUList`, or ndarray
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

    def select_group(self, group_index):
        """
        Select the slice closest to the provided wavelength.

        Parameters
        ----------
        group_index : float
            Group index to select in units of the x-axis of the integration.
            The nearest group will be selected if "snap to slice" is enabled
            in the slice plugin.
        """
        if not isinstance(group_index, int):
            raise TypeError("group_index must be an integer")
        if slice < 0:
            raise ValueError("group_index must be positive")

        msg = SliceSelectSliceMessage(value=group_index, sender=self)
        self.app.hub.broadcast(msg)

    def get_data(self, data_label=None, spatial_subset=None,
                 temporal_subset=None, cls=None, use_display_units=False):
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
        temporal_subset : str, optional
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spatial_subset=spatial_subset,
                              temporal_subset=temporal_subset,
                              cls=cls, use_display_units=use_display_units)
