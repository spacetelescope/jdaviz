from strauss.sonification import Sonification
from strauss.sources import Events, Objects
from strauss import channels
from strauss.score import Score
from strauss.generator import Spectralizer
import numpy as np
from tqdm import tqdm
from contextlib import contextmanager
import sys, os
import time
from astropy import units as u

# some beginner utility functions for STRAUSS + CubeViz


@contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:  
            yield
        finally:
            sys.stderr = old_stderr


def audify_spectrum(spec, duration, overlap=0.05, system='mono', srate=44100, fmin=40, fmax=1300,
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
    
    # again, use maximal range for the mapped parameters
    lims = {'spectrum': ('0', '100')}
    
    # set up source
    sources = Events(data.keys())
    sources.fromdict(data)
    sources.apply_mapping_functions(map_lims=lims)
    
    # render and play sonification!
    soni = Sonification(score, sources, generator, system, samprate=srate)
    soni.render()
    soni._make_seamless(overlap)
    # print(soni.loop_channels)
    # sd.play(soni.loop_channels['0'].values * 0.5,loop=True)
    return soni.loop_channels['0'].values


class CubeListenerData:
    def __init__(self, cube, wlens, samplerate=44100, duration=1, overlap=0.05, buffsize=1024,
                 bdepth=16, wl_bounds=None, wl_unit=None, audfrqmin=50, audfrqmax=1500,
                 eln=False, vol=False):
        self.siglen = int(samplerate*(duration-overlap))
        self.cube = cube
        self.dur = duration
        self.bdepth = bdepth
        self.srate = samplerate
        self.maxval = pow(2, bdepth-1) - 1
        self.fadedx = 0

        if vol:
            self.atten_level = int(np.clip(100/vol, 0, 2**15-1))
        else:
            self.atten_level = 1
        print(vol, self.atten_level)
            
        self.wl_bounds = wl_bounds
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
        
        self.idx1 = 0
        self.idx2 = 0
        self.cbuff = False
        self.cursig = np.zeros(self.siglen, dtype='int16')
        self.newsig = np.zeros(self.siglen, dtype='int16')
        
        if self.cursig.nbytes * pow(1024,-3) > 2:
            raise Exception("Cube projected to be > 2Gb!")
            
        self.sigcube = np.zeros((*self.cube.shape[:2], self.siglen), dtype='int16')

    def set_wl_bounds(self, w1, w2):
        """
        set the wavelength bounds for indexing spectra
        """
        wsrt = np.sort([w1, w2])
        self.wl_bounds = tuple(wsrt)
        print(w1, w2, 'test')
        print(self.wl_bounds)
        
    def audify_cube(self):
        """
        Iterate through the cube, convert each spectrum to a signal, and store
        in class attributes
        """
        lo2hi = self.wlens.argsort()[::-1]
        # if self.wl_bounds:
        #     si_wl_bounds = (self.wl_bounds * getattr(u, self.wl_unit)).to('m')
        #     wdx = np.logical_and(self.wlens >= si_wl_bounds[0].value,
        #                          self.wlens <= si_wl_bounds[1].value)
        #     lo2hi = lo2hi[wdx]
        #     print (wdx, self.wlens, dir(self.wlens))
        t0 = time.time()
        for i in tqdm(range(self.cube.shape[0])):
            for j in range(self.cube.shape[1]):
                with suppress_stderr():
                    if self.cube[i, j, lo2hi].any():
                        sig = audify_spectrum(self.cube[i, j, lo2hi], self.dur,
                                              srate=self.srate,  
                                              fmin=self.audfrqmin,
                                              fmax=self.audfrqmax,
                                              eln=self.eln)
                        sig = (sig*self.maxval).astype('int16')
                        self.sigcube[i, j, :] = sig
                    else:
                        continue
        self.cursig[:] = self.sigcube[self.idx1, self.idx2, :]
        self.newsig[:] = self.cursig[:]
        t1 = time.time()
        print(f"Took {t1-t0}s to process {self.cube.shape[0]*self.cube.shape[1]} spaxels")

    def player_callback(self, outdata, frames, time, status):
        cur = self.cursig
        new = self.newsig
        sdx = int(time.outputBufferDacTime*self.srate)
        dxs = np.arange(sdx, sdx+frames).astype(int) % self.sigcube.shape[-1]  
        if self.cbuff:
            outdata[:, 0] = (cur[dxs] * self.ofade).astype('int16')
            outdata[:, 0] += (new[dxs] * self.ifade).astype('int16')
            self.cursig[:] = self.newsig[:]
            self.cbuff = False
        else:
            outdata[:, 0] = self.cursig[dxs]
        outdata[:, 0] //= self.atten_level
