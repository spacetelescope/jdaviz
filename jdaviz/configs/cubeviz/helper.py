import numpy as np
from astropy.utils.decorators import deprecated
from glue.core import BaseData

from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import (AddDataMessage,
                                SliceSelectSliceMessage)

__all__ = ['Cubeviz']


class Cubeviz(ImageConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_uncert_viewer_reference_name = "uncert-viewer"
    _default_flux_viewer_reference_name = "flux-viewer"
    _default_image_viewer_reference_name = "image-viewer"

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
            for att_name in ["Wave", "Wavelength", "Freq", "Frequency",
                             "Wavenumber", "Velocity", "Energy"]:
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

    def select_slice(self, slice):
        """
        Select a slice by index.

        Parameters
        ----------
        slice : int
            Slice integer to select
        """
        if not isinstance(slice, int):
            raise TypeError("slice must be an integer")
        if slice < 0:
            raise ValueError("slice must be positive")
        msg = SliceSelectSliceMessage(slice=slice, sender=self)
        self.app.hub.broadcast(msg)

    def select_wavelength(self, wavelength):
        """
        Select the slice closest to the provided wavelength.

        Parameters
        ----------
        wavelength : float
            Wavelength to select in units of the x-axis of the spectrum.  The nearest slice will
            be selected.
        """
        if not isinstance(wavelength, (int, float)):
            raise TypeError("wavelength must be a float or int")
        # Retrieve the x slices from the spectrum viewer's marks
        sv = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        x_all = sv.native_marks[0].x
        if sv.state.layers[0].as_steps:
            # then the marks have been doubled in length (each point duplicated)
            x_all = x_all[::2]
        index = np.argmin(abs(x_all - wavelength))
        return self.select_slice(int(index))

    @property
    def specviz(self):
        """
        A Specviz helper (:class:`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Cubeviz.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz


@deprecated('3.2', alternative='Cubeviz')
class CubeViz(Cubeviz):
    """This class is pending deprecation. Please use `Cubeviz` instead."""
    pass


def layer_is_cube_image_data(layer):
    return isinstance(layer, BaseData) and layer.ndim in (2, 3)
