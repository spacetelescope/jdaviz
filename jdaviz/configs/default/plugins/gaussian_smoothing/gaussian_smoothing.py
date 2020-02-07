import numpy as np
from astropy import units as u
from astropy.units import Quantity
from glue.core import DataCollection
from glue.core.edit_subset_mode import (AndMode, AndNotMode, OrMode,
                                        ReplaceMode, XorMode)
from glue.core.message import EditSubsetMessage
from ipyvuetify import VuetifyTemplate
from traitlets import Any, Bool, Dict, Float, Int, List, Unicode

from jdaviz.core.events import DataSelectedMessage, LoadDataMessage
from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from specutils import Spectrum1D
from specutils.manipulation import gaussian_smooth

__all__ = ['GaussianSmoothingButton']


@tools('g-gaussian-smoothing')
class GaussianSmoothingButton(TemplateMixin):
    dialog = Bool(False).tag(sync=True)
    template = load_template("gaussian_smoothing.vue", __file__).tag(sync=True)
    stddev = Float(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def vue_gaussian_smooth(self, *args, **kwargs):
        # TODO: hack because of current incompatibility with ipywidget types
        #  and vuetify templates.

        self.dialog = False

        # Get currently activate data
        # data = self.session.data_collection

        # Testing inputs to make sure putting smoothed spectrum into
        # datacollection works
        input_flux = Quantity(np.array([0.2, 0.3, 2.2, 0.3]), u.Jy)
        input_spaxis = Quantity(np.array([1, 2, 3, 4]), u.micron)
        spec1 = Spectrum1D(input_flux, spectral_axis=input_spaxis)

        # Takes the user input from the dialog (stddev) and uses it to
        # define a standard deviation for gaussian smoothing
        spec1_gsmooth = gaussian_smooth(spec1, stddev=self.stddev)

        dc = DataCollection()

        dc['spec1'] = spec1_gsmooth

        self.data_collection.add(dc['spec1'])
