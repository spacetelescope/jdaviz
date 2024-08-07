from jdaviz.core.events import SliceSelectSliceMessage
from jdaviz.core.events import AddDataMessage
from jdaviz.core.helpers import CubeConfigHelper
from jdaviz.configs.rampviz.plugins.viewers import RampvizImageView

__all__ = ['Rampviz']

_temporal_axis_names = ['group', 'groups']


class Rampviz(CubeConfigHelper):
    """Rampviz Helper class"""
    _default_configuration = 'rampviz'
    _default_group_viewer_reference_name = "group-viewer"
    _default_diff_viewer_reference_name = "diff-viewer"
    _default_integration_viewer_reference_name = "integration-viewer"
    _cube_viewer_default_label = _default_group_viewer_reference_name

    _loaded_flux_cube = None
    _cube_viewer_cls = RampvizImageView

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cube_cache = {}

    def load_data(self, data, data_label=None, **kwargs):
        """
        Load and parse a data cube with Cubeviz.
        (Note that only one cube may be loaded per Cubeviz instance.)

        Parameters
        ----------
        data : str, `~roman_datamodels.datamodels.DataModel`, `~astropy.nddata.NDDataArray` or ndarray
            A string file path, Roman DataModel object pointing to the
            data cube, an NDDataArray, or a Numpy array.
            If plain array is given, axes order must be ``(x, y, z)``.
        data_label : str or `None`
            Data label to go with the given data. If not given,
            one will be automatically generated.
        **kwargs : dict
            Extra keywords accepted by Jdaviz application-level parser.
        """  # noqa
        if data_label:
            kwargs['data_label'] = data_label

        super().load_data(data, parser_reference="ramp-data-parser", **kwargs)

        self.app.hub.subscribe(self, AddDataMessage,
                               handler=self._set_x_axis)

    def _set_x_axis(self, msg):
        viewer = self.app.get_viewer(self._default_group_viewer_reference_name)
        ref_data = viewer.state.reference_data
        viewer.state.x_att = ref_data.id["Pixel Axis 2 [x]"]
        viewer.state.reset_limits()

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
        ``temporal_subset``, if applicable.

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
