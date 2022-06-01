import numpy as np

from jdaviz.core.helpers import ConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import (AddDataMessage,
                                SliceSelectWavelengthMessage,
                                SliceSelectSliceMessage)

__all__ = ['Cubeviz', 'CubeViz']


class Cubeviz(ConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.hub.subscribe(self, SliceSelectWavelengthMessage,
                               handler=self.select_wavelength)
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
        if isinstance(wavelength, SliceSelectWavelengthMessage):
            # SliceSelectWavelengthMessage is broadcasted by the spectrum-viewer slice tool
            wavelength = float(wavelength.wavelength)
        if not isinstance(wavelength, (int, float)):
            raise TypeError("wavelength must be a float or int")
        x_all = self.app.get_viewer('spectrum-viewer').data()[0].spectral_axis.value
        index = np.argmin(abs(x_all - wavelength))
        return self.select_slice(int(index))

    @property
    def specviz(self):
        """
        A specviz helper (`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by cubeviz
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz


# TODO: Officially deprecate this with coordination with JDAT notebooks team.
# For backward compatibility only.
class CubeViz(Cubeviz):
    """This class is pending deprecation. Please use `Cubeviz` instead."""
    pass
