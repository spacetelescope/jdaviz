import numpy as np
from astropy.utils.introspection import minversion

from glue.core import BaseData
from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import (AddDataMessage,
                                SliceSelectSliceMessage)

# NOTE: this and the if-statement that uses it can be removed if/once
# the version of glue-jupyter with as_steps support is pinned as min-version
GLUEJUPYTER_GE_0_13 = minversion('glue_jupyter', '0.13.0')

__all__ = ['Cubeviz', 'CubeViz']


class Cubeviz(ImageConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.hub.subscribe(self, AddDataMessage,
                               handler=self._set_spectrum_x_axis)

    def _set_spectrum_x_axis(self, msg):
        if msg.viewer_id != "cubeviz-3":
            return
        viewer = self.app.get_viewer("spectrum-viewer")
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
                viewer.state.x_att_pixel = ref_data.id["Pixel Axis 2 [x]"]

    def load_data(self, data, **kwargs):
        """
        Load and parse a data cube with Cubeviz.
        (Note that only one cube may be loaded per Cubeviz instance.)

        Parameters
        ----------
        data : str or `~astropy.io.fits.HDUList`
            A string file path or astropy FITS object pointing to the
            data cube.
        """
        if len(self.app.state.data_items) != 0:
            raise RuntimeError('only one cube may be loaded per Cubeviz instance')

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
        sv = self.app.get_viewer('spectrum-viewer')
        x_all = sv.native_marks[0].x
        if sv.state.layers[0].as_steps and GLUEJUPYTER_GE_0_13:
            # then the marks have been doubled in length (each point duplicated)
            x_all = x_all[::2]
        index = np.argmin(abs(x_all - wavelength))
        return self.select_slice(int(index))

    @property
    def specviz(self):
        """
        A Specviz helper (`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Cubeviz.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz


# TODO: Officially deprecate this with coordination with JDAT notebooks team.
# For backward compatibility only.
class CubeViz(Cubeviz):
    """This class is pending deprecation. Please use `Cubeviz` instead."""
    pass


def layer_is_cube_image_data(layer):
    return isinstance(layer, BaseData) and layer.ndim in (2, 3)
