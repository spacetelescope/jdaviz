import numpy as np

from jdaviz.core.helpers import ConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import SliceSelectWavelengthMessage, SliceSelectSliceMessage

__all__ = ['Cubeviz', 'CubeViz']


class Cubeviz(ConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.hub.subscribe(self, SliceSelectWavelengthMessage,
                               handler=self.select_wavelength)

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
        A specviz helper (`~jdaviz.configs.specviz.Specviz`) for the Jdaviz
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
