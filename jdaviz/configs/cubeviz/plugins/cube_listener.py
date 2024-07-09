from strauss.sonification import Sonification
from strauss.sources import Events, Objects
from strauss import channels
from strauss.score import Score
from strauss.generator import Spectralizer
import numpy as np
from tqdm import tqdm
from contextlib import contextmanager
import sys, os

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
            
def audify_spectrum(spec, duration, overlap=0.05, system='mono', srate=44100, fmin=40, fmax=1300):
    notes = [["A2"]]
    score =  Score(notes, duration)
    
    #set up spectralizer generator
    generator = Spectralizer(samprate=srate)

    # Lets pick the mapping frequency range for the spectrum...
    generator.modify_preset({'min_freq':fmin, 'max_freq':fmax})

    data = {'spectrum':[spec], 'pitch':[1]}
    
    # again, use maximal range for the mapped parameters
    lims = {'spectrum': ('0','100')}
    
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
    def __init__(self, cube, wlens, samplerate=44100, duration=1, overlap=0.05, buffsize=1024, bdepth=16):
        self.siglen = int(samplerate*(duration-overlap))
        self.cube = cube
        self.dur = duration
        self.bdepth = bdepth
        self.srate = samplerate
        self.maxval = pow(2,bdepth-1) - 1
        self.fadedx = 0
        
        self.wlens = wlens
        
        # control fades
        fade = np.linspace(0,1, buffsize+1)
        self.ifade = fade[:-1]
        self.ofade = fade[::-1][:-1]
        
        self.idx1 = 0
        self.idx2 = 0
        self.cbuff = False
        self.cursig = np.zeros(self.siglen, dtype='int16')
        self.newsig = np.zeros(self.siglen, dtype='int16')
        
        if self.cursig.nbytes * pow(1024,-3) > 2:
            raise Exception("Cube projected to be > 2Gb!")
            
        self.sigcube = np.zeros((self.siglen, *self.cube.shape[1:]), dtype='int16')
        
    def audify_cube(self, fmin=50, fmax=1500):
        """
        Iterate through the cube, convert each spectrum to a signal, and store
        in class attributes
        """
        lo2hi = self.wlens.argsort()[::-1]
        for i in tqdm(range(self.cube.shape[1])):
            for j in range(self.cube.shape[2]):
                with suppress_stderr():
                    sig = audify_spectrum(self.cube[lo2hi,i,j], self.dur, 
                                          srate=self.srate,  
                                          fmin=fmin, fmax=fmax)
                    sig = (sig*self.maxval).astype('int16')
                    self.sigcube[:,i,j] = sig
        self.cursig[:] = self.sigcube[:,self.idx1,self.idx2]
        self.newsig[:] = self.cursig[:]

    def player_callback(self, outdata, frames, time, status):
        cur = self.cursig
        new = self.newsig
        sdx = int(time.outputBufferDacTime*self.srate)
        dxs = np.arange(sdx, sdx+frames).astype(int) % self.sigcube.shape[0]  
        if self.cbuff:
            outdata[:,0] = (cur[dxs] * self.ofade).astype('int16')
            outdata[:,0] += (new[dxs] * self.ifade).astype('int16')
            self.cursig[:] = self.newsig[:]
            self.cbuff = False
        else:
            outdata[:,0] = self.cursig[dxs] 
