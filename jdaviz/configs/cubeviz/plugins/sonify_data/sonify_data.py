import os
from pathlib import Path

import numpy as np
import specutils
from astropy import units as u
from astropy.nddata import CCDData
from astropy.utils import minversion
from traitlets import Bool, List, Unicode, observe
from specutils import manipulation, analysis, Spectrum1D

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.events import SnackbarMessage, GlobalDisplayUnitChanged
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin,
                                        DatasetSelect, DatasetSelectMixin,
                                        SpectralSubsetSelectMixin,
                                        AddResultsMixin,
                                        SelectPluginComponent,
                                        SpectralContinuumMixin,
                                        skip_if_no_updates_since_last_active,
                                        with_spinner)
from jdaviz.core.validunits import check_if_unit_is_per_solid_angle
from jdaviz.core.user_api import PluginUserApi
from jdaviz.utils import flux_conversion

from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData
import sounddevice as sd


__all__ = ['SonifyData']


@tray_registry('cubeviz-sonify-data', label="Sonify Data",
               viewer_requirements=['spectrum', 'image'])
class SonifyData(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "sonify_data.vue"

    sample_rate = IntHandleEmpty(44100).tag(sync=True)
    buffer_size = IntHandleEmpty(2048).tag(sync=True)
    assidx = FloatHandleEmpty(2.5).tag(sync=True)
    ssvidx = FloatHandleEmpty(0.65).tag(sync=True)
    wavemin = FloatHandleEmpty(15800).tag(sync=True)
    wavemax = FloatHandleEmpty(16000).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.audified_cube = None
        self.stream = None

    def start_stream(self):
        if self.stream:
            self.stream.start()
        else:
            print("unable to start stream")

    def stop_stream(self):
        if self.stream:
            self.stream.stop()
        else:
            print("unable to stop stream")

    def update_cube(self, x, y):
        if not hasattr(self.audified_cube, 'newsig') and not hasattr(self.audified_cube, 'sigcube'):
            print("cube not initialized")
            return
        self.audified_cube.newsig = self.audified_cube.sigcube[:, x, y]
        self.audified_cube.cbuff = True

    def vue_sonify_cube(self, *args):
        self.get_sonified_cube()

    @with_spinner()
    def get_sonified_cube(self):
        viewer = self.app.get_viewer('flux-viewer')
        spectrum = viewer.active_image_layer.layer.get_object(statistic=None)

        clipped_arr = np.clip(spectrum.flux.value.T, 0, np.inf)
        # arr = spectrum[wavemin:wavemax].flux.value.T
        self.audified_cube = CubeListenerData(clipped_arr ** self.assidx, spectrum.wavelength.value, duration=0.8,
                                  samplerate=self.sample_rate, buffsize=self.buffer_size)
        self.audified_cube.audify_cube()
        self.audified_cube.sigcube = (self.audified_cube.sigcube * pow(clipped_arr.sum(0) / clipped_arr.sum(0).max(), self.ssvidx)).astype('int16')
        self.stream = sd.OutputStream(samplerate=self.sample_rate, blocksize=self.buffer_size, channels=1, dtype='int16', latency='low',
                                      callback=self.audified_cube.player_callback)
        self.audified_cube.cbuff = True

        self.app.sonification_enabled = True
