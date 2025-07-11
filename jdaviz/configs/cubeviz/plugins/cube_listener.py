import numpy as np
from contextlib import contextmanager
import multiprocessing as mp
from multiprocessing import Pool
import sys
import os

try:
    from strauss.sonification import Sonification
    from strauss.sources import Events
    from strauss.score import Score
    from strauss.generator import Spectralizer
except ImportError:
    pass

from jdaviz.configs.default.plugins.model_fitting.fitting_backend import generate_spaxel_list

#  smallest fraction of the max audio amplitude that can be represented by a 16-bit signed integer
INT_MAX = 2**15 - 1
MINVOL = 1/INT_MAX


@contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr


def sonify_spectrum(spec, duration, overlap=0.05, system='mono', srate=44100, fmin=40, fmax=1300,
                    eln=False):
    notes = [["A2"]]
    score = Score(notes, duration)
    # set up spectralizer generator
    generator = Spectralizer(samprate=srate)

    # Lets pick the mapping frequency range for the spectrum...
    generator.modify_preset({'min_freq': fmin, 'max_freq': fmax,
                             'fit_spec_multiples': False,
                             'interpolation_type': 'preserve_power',
                             'equal_loudness_normalisation': eln})

    data = {'spectrum': [spec], 'pitch': [1]}

    # set range in spectral flux representing the maximum and minimum sound frequency power:
    # 0 (numeric): absolute 0 in flux units, such that any flux above 0 will sound.
    # '100' (string): 100th percentile (i.e. maximum value) in spectral flux.
    lims = {'spectrum': (0, '%100')}

    # set up source
    sources = Events(data.keys())
    sources.fromdict(data)
    sources.apply_mapping_functions(map_lims=lims)

    # render and play sonification!
    soni = Sonification(score, sources, generator, system, samprate=srate)
    soni.render()
    soni._make_seamless(overlap)

    return soni.loop_channels['0'].values


class CubeListenerData:
    def __init__(self, cube, wlens, samplerate=44100, duration=1, overlap=0.05, buffsize=1024,
                 bdepth=16, wl_unit=None, audfrqmin=50, audfrqmax=1500, eln=False, vol=None,
                 spectral_axis_index=2, n_cpu=None):
        self.siglen = int(samplerate*(duration-overlap))
        self.cube = cube
        self.dur = duration
        self.bdepth = bdepth
        self.srate = samplerate
        self.maxval = pow(2, bdepth-1) - 1
        self.fadedx = 0
        if n_cpu is None:
            self.n_cpu = mp.cpu_count() - 1
        else:
            self.n_cpu = n_cpu
        # Set spectral axis and spatial axes indices for later use
        self.spectral_axis_index = spectral_axis_index
        spatial_inds = [0, 1, 2]
        spatial_inds.remove(self.spectral_axis_index)
        self.spatial_inds = spatial_inds

        if vol is None:
            self.atten_level = 1
        else:
            self.atten_level = int(np.clip((vol/100)**2, MINVOL, 1))

        self.wl_unit = wl_unit
        self.wlens = wlens

        # control fades
        fade = np.linspace(0, 1, buffsize+1)
        self.ifade = fade[:-1]
        self.ofade = fade[::-1][:-1]

        # mapping frequency limits in Hz
        self.audfrqmin = audfrqmin
        self.audfrqmax = audfrqmax

        # do we normalise for equal loudness?
        self.eln = eln

        self.cbuff = False
        self.cursig = np.zeros(self.siglen, dtype='int16')
        self.newsig = np.zeros(self.siglen, dtype='int16')

        # ensure sigcube isn't too big before we initialise it
        slices = [slice(None),]*3
        slices[spectral_axis_index] = 0
        if self.cube[*slices].size * self.siglen * 2 * pow(1024, -3) > 2:
            raise Exception("Cube projected to be > 2Gb!")

        sigcube_shape = list(self.cube.shape)
        sigcube_shape[spectral_axis_index] = self.siglen
        self.sigcube = np.zeros(sigcube_shape, dtype='int16')

    def set_wl_bounds(self, w1, w2):
        """
        set the wavelength bounds for indexing spectra
        """
        wsrt = np.sort([w1, w2])
        self.wl_bounds = tuple(wsrt)

    def sonify_cube(self):
        """
        Iterate through the cube, convert each spectrum to a signal, and store
        in class attributes
        """
        lo2hi = self.wlens.argsort()[::-1]

        spaxels = generate_spaxel_list(self.cube, self.spectral_axis_index)

        # Callback to collect results from workers into the cubes
        def collect_result(results):
            for i in range(len(results['x'])):
                x = results['x'][i]
                y = results['y'][i]
                sig = results['sig'][i]

                # Store fitted values
                if self.spectral_axis_index in [2, -1]:
                    self.sigcube[x, y, :] = sig
                elif self.spectral_axis_index == 0:
                    self.sigcube[:, y, x] = sig

        results = []
        pool = Pool(self.n_cpu)
        for spx in np.array_split(spaxels, self.n_cpu):
            # Worker for the multiprocess pool.
            worker = SonifySpaxelWorker(self.cube, spx, lo2hi, self.dur, self.srate,
                                        self.audfrqmin, self.audfrqmax, self.eln, self.maxval,
                                        spectral_axis_index=self.spectral_axis_index)
            r = pool.apply_async(worker, callback=collect_result)
            results.append(r)
        for r in results:
            r.wait()

        pool.close()

        if self.spectral_axis_index == 2:
            self.cursig[:] = self.sigcube[0, 0, :]
        elif self.spectral_axis_index == 0:
            self.cursig[:] = self.sigcube[:, 0, 0]
        self.newsig[:] = self.cursig[:]

    def player_callback(self, outdata, frames, time, status):
        cur = self.cursig
        new = self.newsig
        sdx = int(time.outputBufferDacTime*self.srate)
        dxs = np.arange(sdx, sdx+frames).astype(int) % self.sigcube.shape[self.spectral_axis_index]
        if self.cbuff:
            outdata[:, 0] = (cur[dxs] * self.ofade).astype('int16')
            outdata[:, 0] += (new[dxs] * self.ifade).astype('int16')
            self.cursig[:] = self.newsig[:]
            self.cbuff = False
        else:
            outdata[:, 0] = self.cursig[dxs]
        outdata[:, 0] //= self.atten_level


class SonifySpaxelWorker:
    """
    A class with callable instances that perform fitting over a
    spaxel. It provides the callable for the `Pool.apply_async`
    function, and also holds everything necessary to perform the
    fit over one spaxel.

    Additionally, the callable computes the realization of the
    model just fitted, over that same spaxel. We cannot do these
    two steps (fit and compute) separately, since we cannot
    modify parameter values in an already built CompoundModel
    instance. We need to use the current model instance while
    it still exists.
    """
    def __init__(self, flux_cube, spaxel_set, lo2hi, dur, srate, audfrqmin, audfrqmax,
                 eln, maxval, spectral_axis_index=2):
        self.cube = flux_cube
        self.spaxel_set = spaxel_set
        self.lo2hi = lo2hi
        self.dur = dur
        self.srate = srate
        self.audfrqmin = audfrqmin
        self.audfrqmax = audfrqmax
        self.eln = eln
        self.maxval = maxval
        self.spectral_axis_index = spectral_axis_index

    def __call__(self):
        results = {'x': [], 'y': [], 'sig': []}

        for spaxel in self.spaxel_set:
            x = spaxel[0]
            y = spaxel[1]
            if self.spectral_axis_index in [2, -1]:
                flux = self.cube[x, y, self.lo2hi]
            elif self.spectral_axis_index == 0:
                flux = self.cube[self.lo2hi, y, x]

            if flux.any():
                sig = sonify_spectrum(flux, self.dur,
                                      srate=self.srate,
                                      fmin=self.audfrqmin,
                                      fmax=self.audfrqmax,
                                      eln=self.eln)
                sig = (sig*self.maxval).astype('int16')
            else:
                continue

            results['x'].append(x)
            results['y'].append(y)
            results['sig'].append(sig)

        return results
