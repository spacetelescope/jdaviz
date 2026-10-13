from specutils import SpectralRegion

class RangeRegion(SpectralRegion):
    '''
    This is a
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _info(self):
        info_str = super()._info()
        return info_str.replace('Spectral', 'Range')